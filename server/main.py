import hashlib
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer

MODEL_ID = os.getenv("MODEL_ID", "ai4bharat/indic-parler-tts")
HF_TOKEN = os.getenv("HF_TOKEN")

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "generated_audio"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Sanskrit Karaoke TTS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

print(f"Loading {MODEL_ID} on {device} ...")

model_kwargs = {}
if HF_TOKEN:
    model_kwargs["token"] = HF_TOKEN

model = ParlerTTSForConditionalGeneration.from_pretrained(
    MODEL_ID,
    torch_dtype=dtype,
    **model_kwargs,
).to(device)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    **model_kwargs,
)

description_tokenizer = AutoTokenizer.from_pretrained(
    model.config.text_encoder._name_or_path,
    **model_kwargs,
)

model.eval()

SANSKRIT_WORD_RE = re.compile(r"\S+", re.UNICODE)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    style: Literal["reading", "chant", "vedic", "meditation"] = "vedic"
    speed: float = Field(default=1.0, ge=0.6, le=1.4)
    pause_ms: int = Field(default=90, ge=0, le=1000)
    # Exact word timing requires word-unit generation.
    # `word` is the default and safest demo mode.
    alignment: Literal["word"] = "word"


class Segment(BaseModel):
    text: str
    start: float
    end: float
    index: int


class GenerateResponse(BaseModel):
    id: str
    audioUrl: str
    duration: float
    sampleRate: int
    segments: list[Segment]


STYLE_DESCRIPTIONS = {
    "reading": (
        "A Sanskrit speaker reads the text clearly and naturally. "
        "The pronunciation is precise, the delivery is calm and steady, "
        "with moderate pitch and moderate speaking rate. "
        "The recording is clean and close with no background noise."
    ),
    "chant": (
        "A Sanskrit speaker performs a devotional Sanskrit chant. "
        "The pronunciation is precise, the delivery is measured and musical, "
        "with a calm devotional tone, clear vowels, natural pauses and a clean "
        "close recording with no background noise."
    ),
    "vedic": (
        "A Sanskrit speaker performs a careful traditional-style Vedic recitation. "
        "The pronunciation is precise and reverent, with a measured chanting pace, "
        "clear Sanskrit vowels, controlled pitch and natural pauses. "
        "The recording is clean and close with no background noise."
    ),
    "meditation": (
        "A Sanskrit speaker delivers the Sanskrit text slowly and peacefully. "
        "The voice is calm, warm and devotional, with a gentle measured pace, "
        "clear pronunciation and natural pauses. "
        "The recording is clean and close with no background noise."
    ),
}


def split_words(text: str) -> list[str]:
    return SANSKRIT_WORD_RE.findall(text.strip())


def normalize_for_filename(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
    return digest


def generate_unit(word: str, description: str) -> np.ndarray:
    """
    Generate one Sanskrit word.

    This is intentionally separate from the whole-verse generation:
    the exact generated duration becomes the timing for that word.
    """
    desc = description

    description_inputs = description_tokenizer(
        desc,
        return_tensors="pt",
    )
    prompt_inputs = tokenizer(
        word,
        return_tensors="pt",
    )

    description_input_ids = description_inputs.input_ids.to(device)
    description_attention_mask = description_inputs.attention_mask.to(device)
    prompt_input_ids = prompt_inputs.input_ids.to(device)
    prompt_attention_mask = prompt_inputs.attention_mask.to(device)

    with torch.inference_mode():
        generation = model.generate(
            input_ids=description_input_ids,
            attention_mask=description_attention_mask,
            prompt_input_ids=prompt_input_ids,
            prompt_attention_mask=prompt_attention_mask,
        )

    audio = generation.detach().float().cpu().numpy().squeeze()

    # Parler generation can occasionally produce a 2-D array.
    if audio.ndim > 1:
        audio = audio.reshape(-1)

    return audio.astype(np.float32)


@app.get("/health")
def health():
    return {
        "ok": True,
        "model": MODEL_ID,
        "device": device,
        "cuda": torch.cuda.is_available(),
        "sampleRate": int(model.config.sampling_rate),
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    words = split_words(req.text)

    if not words:
        raise HTTPException(status_code=400, detail="No Sanskrit text found.")

    # Prevent accidental huge synchronous jobs.
    if len(words) > 250:
        raise HTTPException(
            status_code=400,
            detail="Please generate at most 250 words at a time in this demo.",
        )

    style = STYLE_DESCRIPTIONS[req.style]

    # The model's description controls speaking style.
    # We add speed as natural-language conditioning.
    speed_words = {
        0.6: "very slow",
        0.75: "slow",
        0.9: "slightly slow",
        1.0: "moderate",
        1.15: "slightly fast",
        1.3: "fast",
        1.4: "very fast",
    }
    nearest_speed = min(speed_words, key=lambda x: abs(x - req.speed))
    description = (
        style
        + f" The speaking rate is {speed_words[nearest_speed]}."
    )

    sample_rate = int(model.config.sampling_rate)
    pause = np.zeros(
        int(sample_rate * req.pause_ms / 1000.0),
        dtype=np.float32,
    )

    pieces: list[np.ndarray] = []
    segments: list[Segment] = []
    cursor = 0.0

    # Deterministic word-level timing.
    for index, word in enumerate(words):
        audio = generate_unit(word, description)

        if audio.size == 0:
            continue

        duration = len(audio) / sample_rate
        start = cursor
        end = cursor + duration

        segments.append(
            Segment(
                text=word,
                start=start,
                end=end,
                index=index,
            )
        )

        pieces.append(audio)

        cursor = end

        if index != len(words) - 1 and pause.size:
            pieces.append(pause)
            cursor += len(pause) / sample_rate

    if not pieces:
        raise HTTPException(status_code=500, detail="TTS generated no audio.")

    audio = np.concatenate(pieces)

    # Prevent clipping after concatenation.
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:
        audio = audio / peak * 0.98

    cache_key = normalize_for_filename(
        req.text
        + "|"
        + req.style
        + "|"
        + str(req.speed)
        + "|"
        + str(req.pause_ms)
    )

    filename = f"{cache_key}.wav"
    output_path = AUDIO_DIR / filename

    if not output_path.exists():
        sf.write(
            output_path,
            audio,
            sample_rate,
            subtype="PCM_16",
        )

    duration = len(audio) / sample_rate

    # The Flutter app needs a URL that can be streamed by the browser.
    audio_url = f"/audio/{filename}"

    return GenerateResponse(
        id=str(uuid.uuid4()),
        audioUrl=audio_url,
        duration=duration,
        sampleRate=sample_rate,
        segments=segments,
    )
