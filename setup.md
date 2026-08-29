# Sanskrit Karaoke - Setup Guide

This project consists of a Python FastAPI backend running the Vāgdhenu AI TTS (Text-to-Speech) model, and a Flutter frontend that provides a premium Spotify-style Musixmatch lyrics synchronization experience.

## Prerequisites

1. **Python 3.12+**
2. **Flutter SDK** (configured with Web support)
3. **FFmpeg** (must be installed and available in your system `PATH` for MP3 conversion)

---

## 1. Backend Setup (TTS Server)

The backend uses a local Python environment to run the Vāgdhenu DiT (Diffusion Transformer) and BigVGAN models.

### Installation

1. Navigate to the server directory:
   ```bash
   cd server
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv tts-env
   tts-env\Scripts\activate
   ```
3. Install the requirements (ensure you have the Vāgdhenu dependencies and `f5_tts`):
   ```bash
   pip install -r requirements.txt
   pip install pydub fastapi uvicorn requests soundfile
   ```

### Running the Server

Start the FastAPI server. It will download the necessary models from HuggingFace on the first run and bind to `localhost:8000`.

```bash
python server.py
```

---

## 2. Frontend Setup (Flutter App)

The frontend is a Flutter web app that connects to the local Python TTS server, requesting audio generation and synchronizing the lyrics playback.

### Installation

1. Open a new terminal and navigate to the flutter app:
   ```bash
   cd flutter_app
   ```
2. Fetch the Dart packages:
   ```bash
   flutter pub get
   ```

### Running the App

Launch the app on Google Chrome to view the Karaoke UI:

```bash
flutter run -d chrome
```

## Architecture Notes
- The TTS generation takes place completely locally on the CPU (or CUDA if configured). 
- The Flutter App connects to the server via the `POST /generate` endpoint. The server responds with the MP3 URL (hosted via FastAPI StaticFiles) and line-level timestamps for synchronization.
