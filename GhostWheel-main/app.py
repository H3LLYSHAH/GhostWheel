from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Virtual Steering Wheel", page_icon="🏁", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:1rem;padding-bottom:0}</style>",
    unsafe_allow_html=True,
)
st.title("🏁 Virtual Steering Wheel")
st.caption("Click **Start with camera** inside the game and allow camera access. "
           "Fists = accelerate, open hands = brake, tilt = steer, thumb out = horn.")

html = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
components.html(html, height=720, scrolling=False)
