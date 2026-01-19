# 🎙️ LinguaVid - Universal Video Translator

AI-powered video translation and dubbing using DubSmart.ai, ElevenLabs.io, and Deepdub.ai.

## Features
- 🎯 Three AI dubbing services
- 🌍 Support for 10+ languages
- ⚡ Fast cloud processing
- 🎵 High-quality voice synthesis

## Services
- **DubSmart.ai** - Voice cloning & professional dubbing
- **ElevenLabs.io** - Premium AI voices
- **Deepdub.ai** - Enterprise-grade TTS

## How to Use
1. Select your preferred dubbing service
2. Choose target language
3. Upload your video
4. Download the dubbed result

## Tech Stack
- Streamlit
- MoviePy
- Faster-Whisper
- Deep-Translator
```

## ⚠️ **Important Notes:**

1. **File Size Limits**: Streamlit Community Cloud has a **200MB** file upload limit
2. **Memory**: Limited to **1GB RAM** - large videos may fail
3. **Processing Time**: Limited to **10 minutes** per request
4. **Storage**: Temporary files are auto-cleaned

## 🔧 **Troubleshooting:**

If deployment fails:

1. **Check logs** in Streamlit Cloud dashboard
2. **Verify** `requirements.txt` syntax
3. **Ensure** API keys are in secrets (not hardcoded)
4. **Test locally** first with `streamlit run app.py`

## 🎉 **That's It!**

Your app will be live at:
```
https://[your-app-name].streamlit.app