"""
Virtual Steering Wheel
-----------------------
Control any car/racing game using your hands as a steering wheel — no
extra hardware needed, just a webcam.

How it works
    * Hold both hands up in front of the camera like you're gripping a
      steering wheel.
    * Tilt your hands (imagine rotating the wheel) to steer left/right.
    * Open both hands flat (palms spread) to brake.
    * Keep both hands as fists (or one open) to accelerate.

Under the hood
    * MediaPipe Hands finds 21 landmarks per hand.
    * We use the two wrist points to compute the tilt angle between your
      hands, same idea as reading a real steering wheel's rotation.
    * We use finger-extension counting to tell an open palm from a fist.
    * PyAutoGUI turns that into keyboard input (W/A/S/D) that any
      keyboard-controlled racing game will pick up, exactly like a real
      controller would.

Run it
    pip install -r requirements.txt
    python steering_wheel.py

Press Q in the camera window to quit.
"""

import math
import platform
import time

import cv2
import mediapipe as mp
import pyautogui

# ----------------------------------------------------------------------
# Config — tune these to taste
# ----------------------------------------------------------------------
STEER_DEADZONE_DEG = 12     # tilt angle (deg) below which we go "straight"
STEER_FULL_DEG = 35         # tilt angle at which we're fully locked left/right
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
MIN_DETECTION_CONF = 0.7
MIN_TRACKING_CONF = 0.6

# PyAutoGUI has a small delay before each call by default; turn that off
# so key presses feel instant.
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # move mouse to a screen corner to abort in an emergency

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def open_camera():
    """Pick the right OpenCV camera backend for the current OS."""
    backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
    cam = cv2.VideoCapture(0, backend)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cam


def hand_center(hand_landmarks, w, h):
    """Average of all 21 landmarks -> a stable center point for the hand."""
    xs = [lm.x for lm in hand_landmarks.landmark]
    ys = [lm.y for lm in hand_landmarks.landmark]
    return (sum(xs) / len(xs) * w, sum(ys) / len(ys) * h)


def is_hand_open(hand_landmarks, handedness_label):
    """
    Rough open-palm vs fist detector.
    A finger counts as "extended" if its tip is farther from the wrist
    than its lower knuckle (PIP joint) is. Thumb is handled separately
    since it moves sideways rather than up/down.
    """
    lm = hand_landmarks.landmark
    wrist = lm[mp_hands.HandLandmark.WRIST]

    def extended(tip_id, pip_id):
        tip = lm[tip_id]
        pip = lm[pip_id]
        d_tip = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
        d_pip = math.hypot(pip.x - wrist.x, pip.y - wrist.y)
        return d_tip > d_pip

    fingers = [
        extended(mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
        extended(mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        extended(mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
        extended(mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP),
    ]
    # thumb: compare tip distance from pinky-MCP vs thumb-MCP distance (sideways spread)
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = lm[mp_hands.HandLandmark.THUMB_MCP]
    pinky_mcp = lm[mp_hands.HandLandmark.PINKY_MCP]
    thumb_open = math.hypot(thumb_tip.x - pinky_mcp.x, thumb_tip.y - pinky_mcp.y) > \
        math.hypot(thumb_mcp.x - pinky_mcp.x, thumb_mcp.y - pinky_mcp.y)

    return sum(fingers + [thumb_open]) >= 3  # majority of digits extended = open palm


class KeyState:
    """Only calls keyDown/keyUp when a key's state actually changes."""

    def __init__(self):
        self._down = set()

    def set(self, key, should_be_down):
        if should_be_down and key not in self._down:
            pyautogui.keyDown(key)
            self._down.add(key)
        elif not should_be_down and key in self._down:
            pyautogui.keyUp(key)
            self._down.discard(key)

    def release_all(self):
        for key in list(self._down):
            pyautogui.keyUp(key)
        self._down.clear()


def main():
    cam = open_camera()
    if not cam.isOpened():
        print("Could not open webcam. Check camera permissions and try again.")
        return

    keys = KeyState()
    last_fps_time = time.time()
    frame_count = 0
    fps = 0.0

    with mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=MIN_DETECTION_CONF,
        min_tracking_confidence=MIN_TRACKING_CONF,
    ) as hands:
        try:
            while True:
                ok, frame = cam.read()
                if not ok:
                    break

                frame = cv2.flip(frame, 1)  # mirror so it feels natural
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                steer_angle = 0.0
                both_open = False
                both_fist = False

                if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
                    centers = []
                    openness = []
                    for hand_landmarks, handedness in zip(
                        results.multi_hand_landmarks, results.multi_handedness
                    ):
                        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        centers.append(hand_center(hand_landmarks, w, h))
                        openness.append(
                            is_hand_open(hand_landmarks, handedness.classification[0].label)
                        )

                    # Sort left-to-right so the angle sign is consistent
                    (x1, y1), (x2, y2) = sorted(centers, key=lambda p: p[0])
                    dx, dy = (x2 - x1), (y2 - y1)
                    steer_angle = math.degrees(math.atan2(dy, dx))

                    both_open = all(openness)
                    both_fist = not any(openness)

                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 3)

                # --- Steering ---
                if steer_angle > STEER_DEADZONE_DEG:
                    keys.set("d", True)
                    keys.set("a", False)
                elif steer_angle < -STEER_DEADZONE_DEG:
                    keys.set("a", True)
                    keys.set("d", False)
                else:
                    keys.set("a", False)
                    keys.set("d", False)

                # --- Accelerate / brake ---
                # Open hands flat = brake. Fists (gripping the "wheel") = accelerate.
                keys.set("s", both_open)
                keys.set("w", both_fist and not both_open)

                # --- HUD ---
                frame_count += 1
                if time.time() - last_fps_time >= 1.0:
                    fps = frame_count / (time.time() - last_fps_time)
                    frame_count = 0
                    last_fps_time = time.time()

                status = "BRAKE" if both_open else ("GAS" if both_fist else "COAST")
                cv2.putText(frame, f"Angle: {steer_angle:5.1f} deg", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Status: {status}", (20, 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {fps:4.1f}", (20, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, "Press Q to quit", (20, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                cv2.imshow("Virtual Steering Wheel", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            keys.release_all()
            cam.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
