import streamlit as st
import os
import sys
import tempfile
import requests
import time

# Simplified imports - let Streamlit handle dependencies
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError as e:
    st.error(f"Please wait, installing dependencies... Error: {e}")
    st.stop()

# Import Deepdub client (optional)
DEEPDUB_AVAILABLE = False
try:
    from deepdub import DeepdubClient
    DEEPDUB_AVAILABLE = True
except ImportError:
    pass  # Deepdub is optional

# --- Page Configuration ---
st.set_page_config(
    page_title="LinguaVid - AI Video Translator",
    page_icon="🎙️",
    layout="wide"
)

# --- API Configuration ---
# Use Streamlit secrets for production, fallback to hardcoded for local testing
try:
    DUBSMART_API_KEY = st.secrets["DUBSMART_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    DEEPDUB_API_KEY = st.secrets["DEEPDUB_API_KEY"]
except:
    # Fallback for local development (remove these before deploying!)
    DUBSMART_API_KEY = "peqf95he9tflbm1qa0io31xmx8lf5qv9"
    ELEVENLABS_API_KEY = "cd0b84410b50c12c5cc26c396255966545f1f8a59fc57a18685acff3061c4b8c"
    DEEPDUB_API_KEY = "dd-OUcC8QqbB8yPIzV0kkY8IDcJVbQXb8h0f6884256"

DUBSMART_API_URL = "https://dubsmart.ai/api/v1"
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# --- Language Mapping ---
DUBSMART_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese",
    "he": "Hebrew",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "ko": "Korean"
}

ELEVENLABS_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese (Mandarin)",
    "pt": "Portuguese",
    "pl": "Polish",
    "nl": "Dutch",
    "hi": "Hindi",
    "ko": "Korean",
    "ar": "Arabic"
}

DEEPDUB_LANGUAGES = {
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "es-ES": "Spanish (Spain)",
    "es-MX": "Spanish (Mexico)",
    "fr-FR": "French",
    "de-DE": "German",
    "it-IT": "Italian",
    "ja-JP": "Japanese",
    "zh-CN": "Chinese (Mandarin)",
    "pt-BR": "Portuguese (Brazil)",
    "ru-RU": "Russian",
    "ar-SA": "Arabic",
    "hi-IN": "Hindi",
    "ko-KR": "Korean"
}

# Deepdub voice presets
DEEPDUB_VOICES = {
    "neutral": "eedd9a83-eccc-4c66-b8aa-1d9eb490e57e_prompt-reading-neutral",
    "friendly": "eedd9a83-eccc-4c66-b8aa-1d9eb490e57e_prompt-friendly",
    "professional": "eedd9a83-eccc-4c66-b8aa-1d9eb490e57e_prompt-professional",
    "energetic": "eedd9a83-eccc-4c66-b8aa-1d9eb490e57e_prompt-energetic"
}

# --- DubSmart Video Translator ---
class DubSmartTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def upload_video(self, video_path: str, status_placeholder):
        """Upload video file to DubSmart using presigned URL"""
        status_placeholder.write("📤 Uploading video to DubSmart.ai...")
        
        # Step 1: Get presigned upload URL
        file_ext = os.path.splitext(video_path)[1][1:]
        response = requests.get(
            f"{DUBSMART_API_URL}/upload",
            params={
                "region": "EU",
                "fileExtension": file_ext
            },
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get upload URL: {response.text}")
        
        upload_data = response.json()
        presigned_url = upload_data.get('url')
        file_key = upload_data.get('key')
        
        # Step 2: Upload file to presigned URL
        with open(video_path, 'rb') as f:
            upload_response = requests.put(
                presigned_url,
                data=f,
                headers={'Content-Type': f'video/{file_ext}'}
            )
        
        if upload_response.status_code not in [200, 204]:
            raise Exception(f"File upload failed: {upload_response.text}")
        
        return file_key

    def create_dubbing_project(self, file_key: str, target_lang: str, status_placeholder):
        """Create a dubbing project"""
        status_placeholder.write(f"🎙️ Creating dubbing project for {target_lang}...")
        
        payload = {
            "input": {
                "path": file_key,
                "type": "LOCAL_FILE",
                "voice": "voiceCloning",
                "textCheck": False
            },
            "targetLanguages": [target_lang],
            "title": f"Video Translation - {target_lang}"
        }
        
        response = requests.post(
            f"{DUBSMART_API_URL}/project",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            project_data = response.json()
            return project_data.get('id')
        else:
            raise Exception(f"Project creation failed: {response.text}")

    def check_project_status(self, project_id: str, status_placeholder):
        """Poll project status until completion"""
        status_placeholder.write("⏳ Processing dubbing (this may take a few minutes)...")
        
        max_attempts = 120
        attempt = 0
        last_status = ""
        
        while attempt < max_attempts:
            try:
                response = requests.get(
                    f"{DUBSMART_API_URL}/project/{project_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    project_data = response.json()
                    
                    base_state = project_data.get('base', {}).get('state', 'unknown')
                    stage = project_data.get('stage', 'unknown')
                    progress = project_data.get('base', {}).get('progress', 0)
                    
                    if attempt % 6 == 0:
                        st.write(f"Debug - State: {base_state}, Stage: {stage}, Progress: {progress}%, Attempt: {attempt}")
                    
                    current_status = f"⏳ State: {base_state} | Stage: {stage} | Progress: {progress}%"
                    if current_status != last_status:
                        status_placeholder.write(current_status)
                        last_status = current_status
                    
                    if base_state.lower() in ['done', 'completed', 'finished']:
                        status_placeholder.write("✅ Dubbing completed! Extracting output...")
                        
                        video_result = project_data.get('videoResult')
                        if video_result and video_result.get('value'):
                            st.success("Found complete dubbed video!")
                            return video_result.get('value'), 'video'
                        
                        segments = project_data.get('segments', [])
                        if segments and len(segments) > 0:
                            audio_url = segments[0].get('resultUrl')
                            if audio_url:
                                st.success("Found dubbed audio segment!")
                                return audio_url, 'audio'
                        
                        audio_path = project_data.get('audioPath')
                        if audio_path:
                            st.success("Found audio path!")
                            return audio_path, 'audio'
                        
                        raise Exception(f"Project completed but no output found.")
                    
                    elif base_state.lower() in ['failed', 'error', 'cancelled']:
                        error = project_data.get('base', {}).get('error', 'Unknown error')
                        raise Exception(f"Dubbing failed: {error}")
                    
                    time.sleep(5)
                    
                else:
                    st.error(f"API returned status code {response.status_code}")
                    time.sleep(5)
                    
            except requests.exceptions.RequestException as e:
                st.warning(f"Network error: {str(e)}")
                time.sleep(5)
            
            attempt += 1
        
        raise Exception(f"Project timeout")

    def download_file(self, url: str, save_path: str, status_placeholder):
        """Download file from URL"""
        status_placeholder.write("📥 Downloading output...")
        
        response = requests.get(url, stream=True)
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return save_path
        else:
            raise Exception(f"Download failed: {response.text}")

    def process_video(self, video_path: str, target_lang: str, output_path: str, status_placeholder):
        """Full pipeline: Upload Video → DubSmart → Download → Merge"""

        file_key = self.upload_video(video_path, status_placeholder)
        project_id = self.create_dubbing_project(file_key, target_lang, status_placeholder)
        status_placeholder.write(f"✅ Project created! ID: {project_id}")

        output_url, output_type = self.check_project_status(project_id, status_placeholder)

        if output_type == 'video':
            status_placeholder.write("📥 Downloading complete dubbed video...")
            self.download_file(output_url, output_path, status_placeholder)
            status_placeholder.write("✅ Downloaded dubbed video from DubSmart!")
        else:
            dubbed_audio_path = os.path.join(tempfile.gettempdir(), "dubbed_audio.mp3")
            self.download_file(output_url, dubbed_audio_path, status_placeholder)

            status_placeholder.write("🎬 Merging dubbed audio with video...")
            video = VideoFileClip(video_path)
            new_audio = AudioFileClip(dubbed_audio_path)
            
            if new_audio.duration > video.duration:
                new_audio = new_audio.subclip(0, video.duration)
            
            final_video = video.set_audio(new_audio)
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                verbose=False,
                logger=None
            )

            try:
                video.close()
                new_audio.close()
            except:
                pass
            
            if os.path.exists(dubbed_audio_path):
                try:
                    os.remove(dubbed_audio_path)
                except:
                    pass


# --- ElevenLabs Video Translator ---
class ElevenLabsTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "xi-api-key": api_key
        }

    def create_dubbing(self, video_path: str, target_lang: str, status_placeholder, watermark: bool = True):
        """Create a dubbing project with ElevenLabs"""
        status_placeholder.write("📤 Uploading video to ElevenLabs...")
        
        with open(video_path, 'rb') as f:
            files = {
                'file': (os.path.basename(video_path), f, 'video/mp4')
            }
            data = {
                'target_lang': target_lang,
                'mode': 'automatic',
                'source_lang': 'auto',
                'watermark': 'true' if watermark else 'false'  # Enable watermark for free tier
            }
            
            response = requests.post(
                f"{ELEVENLABS_API_URL}/dubbing",
                headers=self.headers,
                files=files,
                data=data
            )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return result.get('dubbing_id')
        else:
            raise Exception(f"ElevenLabs upload failed: {response.text}")

    def check_dubbing_status(self, dubbing_id: str, status_placeholder):
        """Poll dubbing status until completion"""
        status_placeholder.write("⏳ Processing with ElevenLabs (this may take a few minutes)...")
        
        max_attempts = 120
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(
                    f"{ELEVENLABS_API_URL}/dubbing/{dubbing_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    
                    if attempt % 6 == 0:
                        st.write(f"ElevenLabs Status: {status}, Attempt: {attempt}")
                    
                    status_placeholder.write(f"⏳ ElevenLabs Status: {status}")
                    
                    if status == 'dubbed':
                        status_placeholder.write("✅ ElevenLabs dubbing completed!")
                        return dubbing_id
                    elif status in ['failed', 'error']:
                        error = data.get('error', 'Unknown error')
                        raise Exception(f"ElevenLabs dubbing failed: {error}")
                    
                    time.sleep(5)
                else:
                    st.error(f"Status check failed: {response.status_code}")
                    time.sleep(5)
                    
            except requests.exceptions.RequestException as e:
                st.warning(f"Network error: {str(e)}")
                time.sleep(5)
            
            attempt += 1
        
        raise Exception("ElevenLabs timeout")

    def download_dubbed_file(self, dubbing_id: str, target_lang: str, output_path: str, status_placeholder):
        """Download the dubbed video"""
        status_placeholder.write("📥 Downloading dubbed video from ElevenLabs...")
        
        response = requests.get(
            f"{ELEVENLABS_API_URL}/dubbing/{dubbing_id}/audio/{target_lang}",
            headers=self.headers,
            stream=True
        )
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        else:
            raise Exception(f"Download failed: {response.text}")

    def process_video(self, video_path: str, target_lang: str, output_path: str, status_placeholder, watermark: bool = True):
        """Full pipeline: Upload → Dub → Download"""
        
        dubbing_id = self.create_dubbing(video_path, target_lang, status_placeholder, watermark)
        status_placeholder.write(f"✅ Dubbing created! ID: {dubbing_id}")
        
        self.check_dubbing_status(dubbing_id, status_placeholder)
        
        # Download audio only
        dubbed_audio_path = os.path.join(tempfile.gettempdir(), "elevenlabs_audio.mp3")
        self.download_dubbed_file(dubbing_id, target_lang, dubbed_audio_path, status_placeholder)
        
        # Merge with original video
        status_placeholder.write("🎬 Merging dubbed audio with video...")
        video = VideoFileClip(video_path)
        new_audio = AudioFileClip(dubbed_audio_path)
        
        if new_audio.duration > video.duration:
            new_audio = new_audio.subclip(0, video.duration)
        
        final_video = video.set_audio(new_audio)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        try:
            video.close()
            new_audio.close()
        except:
            pass
        
        if os.path.exists(dubbed_audio_path):
            try:
                os.remove(dubbed_audio_path)
            except:
                pass


# --- Deepdub Video Translator ---
class DeepdubTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = DeepdubClient(api_key=api_key)

    def extract_audio_transcription(self, video_path: str, status_placeholder):
        """Extract audio and transcribe using Whisper"""
        status_placeholder.write("🔍 Extracting audio from video...")
        
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            st.warning("Installing faster-whisper...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "faster-whisper"])
            from faster_whisper import WhisperModel
        
        # Extract audio
        audio_path = os.path.join(tempfile.gettempdir(), "temp_audio.mp3")
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        
        # Transcribe
        status_placeholder.write("🧠 Transcribing audio...")
        model = WhisperModel("base", device="cpu")
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text.strip() + " "
        
        return full_text.strip(), audio_path

    def translate_text(self, text: str, target_lang: str, status_placeholder):
        """Translate text using Google Translator"""
        status_placeholder.write(f"🌐 Translating to {target_lang}...")
        
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            st.warning("Installing deep-translator...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
            from deep_translator import GoogleTranslator
        
        # Extract base language code (e.g., "en-US" -> "en")
        base_lang = target_lang.split('-')[0]
        
        translator = GoogleTranslator(source='auto', target=base_lang)
        translated = translator.translate(text)
        
        return translated

    def generate_speech(self, text: str, voice_id: str, locale: str, status_placeholder):
        """Generate speech using Deepdub TTS"""
        status_placeholder.write("🗣️ Generating AI voice with Deepdub...")
        
        audio_bytes = self.client.tts(
            text=text,
            voice_prompt_id=voice_id,
            model="dd-etts-2.5",
            locale=locale
        )
        
        return audio_bytes

    def process_video(self, video_path: str, target_lang: str, voice_id: str, output_path: str, status_placeholder):
        """Full pipeline: Extract → Transcribe → Translate → TTS → Merge"""
        
        # Step 1: Extract and transcribe
        original_text, audio_path = self.extract_audio_transcription(video_path, status_placeholder)
        st.info(f"📝 Transcribed: {original_text[:100]}...")
        
        # Step 2: Translate
        translated_text = self.translate_text(original_text, target_lang, status_placeholder)
        st.success(f"✅ Translated: {translated_text[:100]}...")
        
        # Step 3: Generate speech
        audio_bytes = self.generate_speech(translated_text, voice_id, target_lang, status_placeholder)
        
        # Save audio
        dubbed_audio_path = os.path.join(tempfile.gettempdir(), "deepdub_audio.mp3")
        with open(dubbed_audio_path, "wb") as f:
            f.write(audio_bytes)
        
        # Step 4: Merge with video
        status_placeholder.write("🎬 Merging dubbed audio with video...")
        video = VideoFileClip(video_path)
        new_audio = AudioFileClip(dubbed_audio_path)
        
        if new_audio.duration > video.duration:
            new_audio = new_audio.subclip(0, video.duration)
        
        final_video = video.set_audio(new_audio)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        # Cleanup
        try:
            video.close()
            new_audio.close()
        except:
            pass
        
        for f in [audio_path, dubbed_audio_path]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass


# --- Main App ---
def main():
    st.title("🎙️ LinguaVid: Universal Video Translator")
    st.markdown("Translate and dub videos using **DubSmart.ai**, **ElevenLabs.io**, or **Deepdub.ai**")

    # Sidebar Settings
    st.sidebar.header("⚙️ Translation Settings")
    
    # Service Selection
    available_services = ["DubSmart.ai", "ElevenLabs.io"]
    if DEEPDUB_AVAILABLE:
        available_services.append("Deepdub.ai")
    
    service = st.sidebar.radio(
        "Select Dubbing Service",
        options=available_services,
        index=0,
        help="Choose which AI service to use for dubbing"
    )
    
    # Language selection based on service
    if service == "DubSmart.ai":
        available_langs = DUBSMART_LANGUAGES
        st.sidebar.info("🚀 DubSmart.ai - Voice cloning & professional dubbing")
    elif service == "ElevenLabs.io":
        available_langs = ELEVENLABS_LANGUAGES
        st.sidebar.info("🎵 ElevenLabs.io - High-quality AI voices")
        
        # Watermark option for ElevenLabs
        watermark = st.sidebar.checkbox(
            "Add ElevenLabs Watermark",
            value=True,
            help="Free tier requires watermark. Uncheck only if you have Creator+ subscription."
        )
        if watermark:
            st.sidebar.warning("⚠️ Video will have ElevenLabs watermark (free tier)")
        else:
            st.sidebar.success("✅ No watermark (requires Creator+ subscription)")
    else:  # Deepdub
        available_langs = DEEPDUB_LANGUAGES
        st.sidebar.info("🎯 Deepdub.ai - Enterprise-grade TTS")
        
        # Voice selection for Deepdub
        voice_style = st.sidebar.selectbox(
            "Voice Style",
            options=list(DEEPDUB_VOICES.keys()),
            index=0,
            format_func=lambda x: x.capitalize(),
            help="Choose the voice style for dubbing"
        )
        voice_id = DEEPDUB_VOICES[voice_style]
    
    target_lang = st.sidebar.selectbox(
        "Target Language",
        options=list(available_langs.keys()),
        index=0,
        format_func=lambda x: available_langs.get(x, x)
    )

    # Service comparison
    with st.sidebar.expander("📊 Service Comparison"):
        st.markdown("""
        **DubSmart.ai:**
        - ✅ Voice cloning
        - ✅ Automatic translation
        - ✅ Multiple languages
        - ⚡ Faster processing
        
        **ElevenLabs.io:**
        - ✅ Premium AI voices
        - ✅ Natural speech
        - ✅ High accuracy
        - 🎯 Best quality
        
        **Deepdub.ai:**
        - ✅ Enterprise TTS
        - ✅ Multiple voice styles
        - ✅ Custom voices
        - 🔧 Fine control
        """)

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload video (MP4, MOV, AVI)",
        type=["mp4", "mov", "avi"]
    )

    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📹 Original Video")
            st.video(uploaded_file)

        if st.button("🚀 Start Translation & Dubbing", type="primary"):
            input_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.read())

            output_path = os.path.join(
                tempfile.gettempdir(),
                f"dubbed_{uploaded_file.name}"
            )

            try:
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                st.info(f"💡 Processing with **{service}**. This may take 2-5 minutes...")
                
                # Select translator based on service
                if service == "DubSmart.ai":
                    translator = DubSmartTranslator(api_key=DUBSMART_API_KEY)
                    translator.process_video(
                        video_path=input_path,
                        target_lang=target_lang,
                        output_path=output_path,
                        status_placeholder=status_box
                    )
                elif service == "ElevenLabs.io":
                    translator = ElevenLabsTranslator(api_key=ELEVENLABS_API_KEY)
                    translator.process_video(
                        video_path=input_path,
                        target_lang=target_lang,
                        output_path=output_path,
                        status_placeholder=status_box,
                        watermark=watermark
                    )
                else:  # Deepdub
                    translator = DeepdubTranslator(api_key=DEEPDUB_API_KEY)
                    translator.process_video(
                        video_path=input_path,
                        target_lang=target_lang,
                        voice_id=voice_id,
                        output_path=output_path,
                        status_placeholder=status_box
                    )

                progress_bar.progress(100)
                status_box.success(f"✅ Translation Complete with {service}!")

                with col2:
                    st.subheader("🎬 Dubbed Video")
                    st.video(output_path)
                    
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="📥 Download Dubbed Video",
                            data=file,
                            file_name=f"dubbed_{uploaded_file.name}",
                            mime="video/mp4"
                        )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info(f"Please check your {service} API key and internet connection.")

            finally:
                for f in [input_path, output_path]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass
    else:
        st.info("📹 Upload a video to start the translation and dubbing process.")
        
        # Features
        st.markdown("### ✨ Features")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("**🎯 Three Services**")
            st.write("DubSmart, ElevenLabs & Deepdub")
        
        with col_b:
            st.markdown("**🌍 Multi-Language**")
            st.write("Support for 10+ languages")
        
        with col_c:
            st.markdown("**⚡ Fast & Quality**")
            st.write("AI-powered dubbing")


if __name__ == "__main__":
    main()