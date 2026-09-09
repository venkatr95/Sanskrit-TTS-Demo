import os
import sys
import site

# HOTFIX: Docker host library poisoning causes cudnnGetVersion crash. 
# We force the process to restart itself with the correct pip library path!
if "CUDNN_FIXED" not in os.environ:
    try:
        cudnn_lib = os.path.join(site.getsitepackages()[0], "nvidia", "cudnn", "lib")
        os.environ["LD_LIBRARY_PATH"] = f"{cudnn_lib}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        os.environ["CUDNN_FIXED"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        pass

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import io
import scipy.io.wavfile as wavfile
import os
import sys
import numpy as np
import torchaudio
import soundfile as sf

def _patched_load(filepath, *args, **kwargs):
    wav, sr = sf.read(filepath)
    if wav.ndim == 1:
        wav = wav[None, :]
    elif wav.ndim == 2:
        wav = wav.T
    return torch.from_numpy(wav).float(), sr

torchaudio.load = _patched_load


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vāgdhenu TTS Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class TTSRequest(BaseModel):
    text: str
    description: str

class GenerateRequest(BaseModel):
    text: str
    style: str
    speed: float = 1.0
    pause_ms: int = 90
    alignment: str = "word"

device = "cuda" if torch.cuda.is_available() else "cpu"

VAGDHENU_DIR = os.path.join(os.path.dirname(__file__), "vagdhenu_repo")
sys.path.insert(0, os.path.join(VAGDHENU_DIR, "src"))
os.environ["PYTHONPATH"] = os.path.join(VAGDHENU_DIR, "BigVGAN") + os.pathsep + os.environ.get("PYTHONPATH", "")
sys.path.insert(0, os.path.join(VAGDHENU_DIR, "BigVGAN"))

# Hack to allow importing render.py without ArgumentParser crashing
sys.argv = ['render.py', '--shard', 'dummy.json', '--results', 'dummy.json']
import prep_text as PT
import bigvgan
from f5_tts.infer.utils_infer import load_model, load_vocoder, infer_process
from f5_tts.model import DiT
from render import (
    get_ref, _ends_halant, _stitch, gate, 
    _anusvara_m, _satva, _hna_metathesis, _vocalic_l, _danda_fix, n_aksharas
)

print(f"Loading Vagdhenu models onto {device}...")
CHAMP = os.path.join(VAGDHENU_DIR, "models")
vocab = os.path.join(CHAMP, "vocab.txt")

CFG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
# Note: forced device to CPU/CUDA based on availability instead of hardcoding
cfm = load_model(DiT, CFG, mel_spec_type="vocos", vocab_file=vocab, device=device)

voice_path = os.path.join(CHAMP, "voice_steer_ema_2026-06-17.pt")
ck = torch.load(voice_path, map_location="cpu", weights_only=True)
ema = {k.replace("ema_model.", ""): v for k, v in ck["ema_model_state_dict"].items() if k not in ("initted", "step")}
cfm.load_state_dict(ema, strict=False)
cfm.eval()

real_voc = load_vocoder("vocos")
class Cap:
    def __init__(s, r): s.r = r; s.last = None
    def decode(s, m): s.last = m.detach().cpu().numpy(); return s.r.decode(m)
cap = Cap(real_voc)

# Initialize BigVGAN vocoder
g = bigvgan.BigVGAN.from_pretrained("nvidia/bigvgan_v2_24khz_100band_256x", use_cuda_kernel=False)
voc_path = os.path.join(CHAMP, "voc_bigvgan_EMA_2026-06-11.pth")
bsd = torch.load(voc_path, map_location="cpu")
bsd = bsd.get("model", bsd)
g.load_state_dict(bsd)
g.remove_weight_norm()
g = g.to(device).eval()

for p in g.parameters(): p.requires_grad = False

def bvgan(mel):
    m = torch.from_numpy(mel).to(device)
    with torch.no_grad():
        if m.dim()==3 and m.shape[1]!=100 and m.shape[2]==100: m = m.transpose(1,2)
        return g(m).squeeze().cpu().numpy().astype(np.float32)

def generate_audio_core(text: str, meter: str):
    print(f"Generating for meter: {meter}")
    
    # Format the verse pieces based on Padas
    text = text.replace("\n", " ")
    pieces = []
    for line in text.split("।"):
        for hemistich in line.split("॥"):
            if hemistich.strip():
                pieces.append(hemistich.strip())
                
    if not pieces: 
        pieces = [text]
        
    ref_audio, ref_t, sps, ref_len = get_ref(meter)
    
    PIECES = [PT.model_text_sandhi(p, echo_final=False) for p in pieces]
    PIECES = [_satva(x) for x in PIECES]
    PIECES = [_danda_fix(_anusvara_m(x)) for x in PIECES]
    PIECES = [_hna_metathesis(x) for x in PIECES]
    PIECES = [_vocalic_l(x) for x in PIECES]
    
    NSYLL = [n_aksharas(x) for x in PIECES]
    SR = 24000
    gap = 0.55
    gap_halant = 0.20
    GAPS = [np.zeros(int(gap*SR) + (int(gap_halant*SR) if _ends_halant(_p) else 0), dtype=np.float32) for _p in PIECES]
    
    bseg = []
    for i, p in enumerate(PIECES):
        torch.manual_seed(60) # Consistent chanting seed
        _fixd = (ref_len + NSYLL[i]*sps) if (sps > 0 and NSYLL) else None
        
        w, sr, _ = infer_process(ref_audio, ref_t, p, cfm, cap, mel_spec_type="vocos", speed=0.90, nfe_step=16, cfg_strength=3.0, device=device, fix_duration=_fixd)
        w = np.array(w, dtype=np.float32)
        if np.abs(w).max() > 1.5: w = w/32768.0
        
        y = bvgan(cap.last)
        mx = np.abs(y).max()
        if mx > 1: y = y/mx*0.97
        bseg.append(y)
        
    _slp = PT.align_slp1(pieces[0]) if pieces else ""
    fric = bool(_slp) and _slp[0] in ("S", "z", "s", "h")
    halant = _ends_halant(PIECES[-1])
    final = _stitch(bseg, GAPS, fric=fric, halant=halant)
    return final, SR, pieces, bseg, GAPS

@app.post("/v1/tts")
async def generate_speech(request: TTSRequest):
    try:
        meter = request.description.strip()
        if not meter:
            meter = "vasantatilaka"
            
        final, SR, _, _, _ = generate_audio_core(request.text, meter)
        
        wav_io = io.BytesIO()
        wavfile.write(wav_io, SR, final)
        wav_io.seek(0)

        import pydub
        audio = pydub.AudioSegment.from_wav(wav_io)
        mp3_io = io.BytesIO()
        audio.export(mp3_io, format="mp3")
        mp3_io.seek(0)

        return StreamingResponse(mp3_io, media_type="audio/mpeg")

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate_karaoke(req: GenerateRequest):
    try:
        style_map = {
            "vedic": "anushtubh",
            "chant": "vasantatilaka",
            "meditation": "gayatri",
            "reading": "anushtubh"
        }
        meter = style_map.get(req.style, "anushtubh")
        
        final, SR, pieces, bseg, GAPS = generate_audio_core(req.text, meter)
        
        # Save to MP3 in static folder
        import pydub
        wav_io = io.BytesIO()
        wavfile.write(wav_io, SR, final)
        wav_io.seek(0)
        
        audio = pydub.AudioSegment.from_wav(wav_io)
        filename = f"{uuid.uuid4().hex}.mp3"
        out_path = os.path.join("static", filename)
        audio.export(out_path, format="mp3")
        
        # Compute line-level timestamps from chunk lengths
        segments = []
        current_time = 0.0
        for i, chunk in enumerate(bseg):
            start = current_time
            duration = len(chunk) / SR
            end = start + duration
            segments.append({
                "text": pieces[i],
                "start": start,
                "end": end,
                "index": i
            })
            current_time = end + (len(GAPS[i]) / SR)
            
        return {
            "audioUrl": f"/static/{filename}",
            "duration": current_time,
            "sampleRate": SR,
            "segments": segments
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
