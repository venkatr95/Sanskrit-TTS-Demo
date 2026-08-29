# Sanskrit Karaoke TTS — Flutter Web + Indic Parler-TTS

A complete example of a Musicmatch-style Sanskrit reader:

- Flutter Web frontend
- FastAPI backend
- AI4Bharat `ai4bharat/indic-parler-tts`
- Sanskrit text input
- Generates audio on the server; the browser streams/plays it
- Word-by-word synchronization
- Auto-scroll to the spoken word
- Play / pause / stop / seek
- Speech style and speed controls

## Architecture

Flutter Web -> FastAPI -> Indic Parler-TTS -> WAV + timing JSON -> Flutter audio player

The demo uses **word-unit synthesis** to obtain deterministic word timings:
each word is synthesized separately and concatenated. This makes the
karaoke timing exact, but it is not as natural as continuous-sentence TTS.

For production Vedic chanting, replace the `word` alignment mode with a
forced-alignment service/model while continuing to use the same Flutter
timing format.

## 1. Hugging Face access

The model is gated. Log into Hugging Face and accept the model's access
conditions:

https://huggingface.co/ai4bharat/indic-parler-tts

Then either:

    huggingface-cli login

or set:

    HF_TOKEN=hf_...

## 2. Server

Recommended: NVIDIA GPU with CUDA.

Create an environment and install:

    cd server
    python -m venv .venv
    # Linux/macOS:
    source .venv/bin/activate
    # Windows:
    # .venv\Scripts\activate

    pip install -r requirements.txt

Run:

    export HF_TOKEN=hf_...
    uvicorn main:app --host 0.0.0.0 --port 8000

The API will be available at:

    http://localhost:8000

## 3. Flutter

Install Flutter, then:

    cd flutter_app
    flutter pub get
    flutter run -d chrome --web-port 8080

If the API is not on localhost:8000, start Flutter with:

    flutter run -d chrome --dart-define=API_BASE_URL=http://YOUR_SERVER:8000

## 4. Example

Paste:

    अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम् ।

Choose `Vedic / devotional`, then Generate & Play.

The frontend receives:

    {
      "audioUrl": "...",
      "segments": [
        {"text":"अग्निमीळे","start":0.0,"end":1.1},
        ...
      ]
    }

The player compares its current audio position with the segment timings
and highlights the active Sanskrit word.

## Production notes

1. Do not expose your Hugging Face token to Flutter.
2. Put the TTS server behind HTTPS.
3. Cache generated verses/audio by a hash of:
   text + style + speed + speaker.
4. Use a GPU worker queue for generation.
5. For natural continuous chanting, generate whole lines/verses and use
   forced alignment to obtain word/syllable timestamps.
6. For Vedic svara, add separate annotation metadata for udatta,
   anudatta and svarita rather than trying to infer it from audio.
