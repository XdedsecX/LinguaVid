import streamlit as st

try:
    from moviepy import VideoFileClip
    st.success("✅ MoviePy imported successfully!")
except ImportError as e:
    st.error(f"❌ Import failed: {e}")

st.write("Streamlit is working!")