# GhostWheel

# Virtual Steering Wheel

Control any keyboard-driven car/racing game using your hands as a steering
wheel — no extra hardware, just a webcam.

## How to play

- Hold both hands up in front of the camera like you're gripping a steering
  wheel.
- **Tilt** your hands (as if rotating a real wheel) to steer left/right
  (`A` / `D`).
- **Open both hands flat** (spread palms) to brake (`S`).
- **Make fists** with both hands to accelerate (`W`).
- Press `Q` in the camera window to quit.

## Setup

1. Install Python 3.9+ from https://www.python.org/ if you don't have it.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run it:
   ```
   python steering_wheel.py
   ```
4. Grant camera permission when your OS prompts you (macOS: System
   Settings → Privacy & Security → Camera → enable for Terminal / your
   Python launcher).
5. Open your racing game (anything that uses W/A/S/D or arrow-key-style
   controls works — e.g. many browser racing games, or games where you've
   rebound controls to WASD).

## How it works

- **MediaPipe Hands** finds 21 3D landmarks per hand from the webcam feed
  in real time.
- **Steering**: we take the center point of each hand and compute the tilt
  angle of the line between them, exactly like reading the rotation of a
  physical steering wheel. Past a small dead-zone, that angle maps to
  `A` (left) or `D` (right).
- **Accelerate/brake**: we count how many fingers are extended per hand to
  tell an open palm from a fist. Both palms open → brake (`S`). Both fists
  → accelerate (`W`).
- **PyAutoGUI** simulates the actual key presses, so any game that reads
  keyboard input treats it exactly like normal typing/controller input.

## Tuning

Open `steering_wheel.py` and adjust these constants near the top:

- `STEER_DEADZONE_DEG` — how many degrees of tilt to ignore before steering
  kicks in (bigger = more forgiving, less twitchy).
- `STEER_FULL_DEG` — currently used as a reference for "full lock" tilt
  (handy if you extend this to analog/proportional steering instead of
  simple key taps).
- `MIN_DETECTION_CONF` / `MIN_TRACKING_CONF` — MediaPipe confidence
  thresholds; raise them if it's picking up false hand detections, lower
  them if it's struggling to see your hands in low light.

## Notes

- Works on macOS and Windows — the script auto-detects the OS and picks
  the right OpenCV camera backend (`AVFoundation` on macOS, `CAP_ANY` /
  DirectShow-MSMF on Windows).
- Good, even lighting on your hands makes tracking noticeably more
  reliable.
- Because this sends real keyboard events, keep the game window focused
  while playing.
