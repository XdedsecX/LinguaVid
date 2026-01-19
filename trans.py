import streamlit as st
import os
import sys
import tempfile
import requests
import time
import ffmpeg

# --------------------------------------------------------------------
# STREAMLIT CONFIG
# --------------------------------------------------------------------
st.set_page_config(
    page_title="LinguaVid - AI Video Translator",
    page_icon="🎙️",
    layout="wide"
)

# --------------------------------------------------------------------
# API KEYS (Secrets → fallback dev)
# --------------------------------------------------------------------
try:
    DUBSMART_API_KEY = st.secrets["DUBSMART_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    DEEPDUB_API_KEY = st.secrets["DEEPDUB_API_KEY"]
except:
    DUBSMART_API_KEY = "peqf95he9tflbm1qa0io31xmx8lf5qv9"
    ELEVENLABS_API_KEY = "cd0b84410b50c12c5cc26c396255966545f1f8a59fc57a18685acff3061c4b8c"
    DEEPDUB_API_KEY = "YOUR_DEEPDUB_GO_KEY"

# --------------------------------------------------------------------
# API BASE URLS
# --------------------------------------------------------------------
DUBSMART_API_URL = "https://dubsmart.ai/api/v1"
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
DEEPDUB_API_URL = "https://api.deepdub.ai/go/v1"   # Deepdub GO API

# --------------------------------------------------------------------
# LANG MAP
# --------------------------------------------------------------------
LANGS = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "ko": "Korean",
    "he": "Hebrew"
}

# --------------------------------------------------------------------
# DUBSMART TRANSLATOR
# --------------------------------------------------------------------
class DubSmartTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def upload(self, video_path, status):
        status.write("📤 Uploading to DubSmart...")
        ext = os.path.splitext(video_path)[1][1:]

        r = requests.get(
            f"{DUBSMART_API_URL}/upload",
            params={"region": "EU", "fileExtension": ext},
            headers=self.headers
        )
        r.raise_for_status()
        data = r.json()

        with open(video_path, "rb") as f:
            up = requests.put(data["url"], data=f, headers={"Content-Type": f"video/{ext}"})
            if up.status_code not in [200, 204]:
                raise Exception(f"Upload failed: {up.text}")

        return data["key"]

    def create(self, file_key, lang, status):
        status.write("🎙️ Creating DubSmart project...")
        payload = {
            "input": {
                "path": file_key,
                "type": "LOCAL_FILE",
                "voice": "voiceCloning",
                "textCheck": False
            },
            "targetLanguages": [lang],
            "title": f"Video → {lang}"
        }
        r = requests.post(f"{DUBSMART_API_URL}/project", headers=self.headers, json=payload)
        r.raise_for_status()
        return r.json()["id"]

    def poll(self, pid, status):
        status.write("⏳ Processing (DubSmart)...")
        for _ in range(360):
            r = requests.get(f"{DUBSMART_API_URL}/project/{pid}", headers=self.headers)
            r.raise_for_status()
            d = r.json()

            s = d.get("base", {}).get("state", "")
            status.write(f"State: {s}")

            if s.lower() in ["done", "completed"]:
                vr = d.get("videoResult")
                if vr and vr.get("value"):
                    return vr["value"], "video"

                seg = d.get("segments", [])
                if seg and seg[0].get("resultUrl"):
                    return seg[0]["resultUrl"], "audio"
                raise Exception("Completed but no asset.")

            if s.lower() in ["failed", "error"]:
                raise Exception("DubSmart failed.")

            time.sleep(5)

        raise Exception("DubSmart timeout")

    def download(self, url, out, status):
        status.write("📥 Downloading DubSmart asset...")
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(out, "wb") as f:
            for c in r.iter_content(8192):
                f.write(c)
        return out

# --------------------------------------------------------------------
# ELEVENLABS TRANSLATOR
# --------------------------------------------------------------------
class ElevenLabsTranslator:
    def __init__(self, api_key):
        self.headers = {"xi-api-key": api_key}

    def create(self, video_path, lang, status):
        status.write("📤 Uploading to ElevenLabs...")
        with open(video_path, "rb") as f:
            files = {"file": (os.path.basename(video_path), f, "video/mp4")}
            data = {"target_lang": lang, "mode": "automatic", "source_lang": "auto"}
            r = requests.post(f"{ELEVENLABS_API_URL}/dubbing", headers=self.headers, files=files, data=data)
        r.raise_for_status()
        return r.json()["dubbing_id"]

    def poll(self, did, status):
        status.write("⏳ Processing (ElevenLabs)...")
        for _ in range(360):
            r = requests.get(f"{ELEVENLABS_API_URL}/dubbing/{did}", headers=self.headers)
            r.raise_for_status()
            d = r.json()
            s = d.get("status", "")
            status.write(f"Status: {s}")
            if s == "dubbed":
                return did
            if s in ["error", "failed"]:
                raise Exception("ElevenLabs failed.")
            time.sleep(5)
        raise Exception("ElevenLabs timeout")

    def download_audio(self, did, lang, out, status):
        status.write("📥 Downloading EL audio...")
        r = requests.get(f"{ELEVENLABS_API_URL}/dubbing/{did}/audio/{lang}", headers=self.headers, stream=True)
        r.raise_for_status()
        with open(out, "wb") as f:
            for c in r.iter_content(8192):
                f.write(c)
        return out

# --------------------------------------------------------------------
# DEEPDUB GO TRANSLATOR
# --------------------------------------------------------------------
class DeepDubGoTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }

    def send(self, video_path, lang, status):
        status.write("📤 Uploading to Deepdub GO...")
        with open(video_path, "rb") as f:
            files = {"file": (os.path.basename(video_path), f, "video/mp4")}
            data = {"target_language": lang, "source_language": "auto"}
            r = requests.post(f"{DEEPDUB_API_URL}/dub", headers=self.headers, files=files, data=data)
        r.raise_for_status()
        return r.json()["id"]

    def poll(self, rid, status):
        status.write("⏳ Processing (Deepdub GO)...")
        for _ in range(360):
            r = requests.get(f"{DEEPDUB_API_URL}/dub/{rid}", headers=self.headers)
            r.raise_for_status()
            d = r.json()
            s = d.get("status", "")
            status.write(f"Status: {s}")
            if s == "completed":
                return d.get("audio_url")
            if s in ["error", "failed"]:
                raise Exception("Deepdub failed.")
            time.sleep(5)
        raise Exception("Deepdub timeout")

# --------------------------------------------------------------------
# FFMPEG MERGE
# --------------------------------------------------------------------
def merge_audio_video(input_video, input_audio, output):
    video_stream = ffmpeg.input(input_video)
    audio_stream = ffmpeg.input(input_audio)

    out = ffmpeg.output(
        video_stream.video,
        audio_stream.audio,
        output,
        vcodec="libx264",
        acodec="aac",
        shortest=None,
        strict="-2"
    )
    ffmpeg.run(out, overwrite_output=True)
    return output

# --------------------------------------------------------------------
# UI
# --------------------------------------------------------------------
st.title("🎙️ LinguaVid — AI Video Translator")
st.write("Translate your videos into multiple languages using AI-powered dubbing services.") 
st.write("Supported providers: DubSmart.ai, ElevenLabs, Deepdub GO")

user ="ameed"
password ="J8aY6Uu2wG6dteM"
video = None

username = st.sidebar.text_input("Enter your name", "Type here...")
userpassword = st.sidebar.text_input("Enter your password", "Type here...", type="password")

if user == username and password == userpassword:
    st.balloons()
    video = st.sidebar.file_uploader("Upload video", type=["mp4", "mov", "mkv"])
    provider = st.sidebar.selectbox("please select the Provider", ["DubSmart.ai", "ElevenLabs", "Deepdub GO"])
    target = st.sidebar.selectbox("Target language", list(LANGS.keys()))

if video and st.button("Translate"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video.read())
        video_path = tmp.name

    status = st.empty()

    out_path = os.path.join(tempfile.gettempdir(), "output.mp4")
    audio_tmp = os.path.join(tempfile.gettempdir(), "dub_audio.mp3")

    try:
        if provider == "DubSmart.ai":
            d = DubSmartTranslator(DUBSMART_API_KEY)
            fk = d.upload(video_path, status)
            pid = d.create(fk, target, status)
            url, typ = d.poll(pid, status)

            if typ == "video":
                d.download(url, out_path, status)
            else:
                d.download(url, audio_tmp, status)
                merge_audio_video(video_path, audio_tmp, out_path)

        elif provider == "ElevenLabs":
            e = ElevenLabsTranslator(ELEVENLABS_API_KEY)
            did = e.create(video_path, target, status)
            e.poll(did, status)
            e.download_audio(did, target, audio_tmp, status)
            merge_audio_video(video_path, audio_tmp, out_path)

        else:  # Deepdub GO
            g = DeepDubGoTranslator(DEEPDUB_API_KEY)
            rid = g.send(video_path, target, status)
            url = g.poll(rid, status)

            r = requests.get(url)
            r.raise_for_status()
            with open(audio_tmp, "wb") as f:
                f.write(r.content)

            merge_audio_video(video_path, audio_tmp, out_path)

        status.write("✅ Done!")
        st.video(out_path)

    except Exception as e:
        st.error(f"Error: {e}")

st.sidebar.write("by Khaid Idies")