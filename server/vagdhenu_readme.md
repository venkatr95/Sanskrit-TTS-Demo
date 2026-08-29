---
language:
- sa
license: apache-2.0
pipeline_tag: text-to-speech
base_model: ai4bharat/IndicF5
tags:
- sanskrit
- chant
- text-to-speech
- f5-tts
- indicf5
- bigvgan
---

# Vāgdhenu — Sanskrit Chant TTS (weights)

Model weights for [**Vāgdhenu**](https://github.com/prathoshap/vagdhenu), a single-speaker Sanskrit **chant (pārāyaṇa) TTS**. MOS ~4.6 (expert listener); conjuncts including retroflex aspirates render 100% correctly.

## Files
| file | what |
|---|---|
| `voice_steer_ema_2026-06-17.pt` | **Production voice** — voice-steered, more reference-responsive (the recommended default). |
| `voice_armA_ema_2026-06-11.pt` | Fallback — reference-driven chant (voice + swara + pace from the reference clip). |
| `voc_bigvgan_EMA_2026-06-11.pth` | **Vocoder** — NVIDIA BigVGAN-v2 fine-tuned on F5 vocos-mel (mandatory; vocos shivers on long vowels). |

The base DiT + `vocab.txt` come from [`ai4bharat/IndicF5`](https://huggingface.co/ai4bharat/IndicF5) (auto-downloaded by the repo's setup).

## Architecture
IndicF5 / F5-TTS — flow-matching **DiT** (OT-CFM mel-infilling, dim 1024 / depth 22 / heads 16, ~337M params, **no native duration or pitch head**) → BigVGAN-v2 vocoder. Sanskrit is routed through **Kannada script** (Devanagari triggers Hindi schwa-deletion).

## Usage
See the [GitHub repo](https://github.com/prathoshap/vagdhenu) — `bash scripts/setup.sh` downloads these weights to `models/`, then `python src/render.py ...` renders a Devanagari verse + meter to a chanted wav.

**The key lever is the reference** (F5 prosody is text-driven, not designable): supply the prosody you want as a clean, exactly-matched reference clip (the *half-reference rule* — `ref_text` must match the reference audio's spoken span on a word/daṇḍa boundary). A per-meter reference bank ships with the repo.

## Training
Fine-tuned from IndicF5 on a ~5 h single-speaker Sanskrit chant corpus ([`prathoshap/vagdhenu-data`](https://huggingface.co/datasets/prathoshap/vagdhenu-data)); the production voice adds a voice-steering retrain on paired clips. Full method in the repo's `docs/TECH_REPORT.md`.

## Intended use & limitations
Synthesis of classical Sanskrit chant (pārāyaṇa) for recitation, study, and accessibility. **No Vedic svaras.** Prosody is **reference-driven**, not arbitrarily designable. The voice is the author's own — please use responsibly and do not impersonate.

## License & attribution
Our contribution under **Apache-2.0**. Built on **AI4Bharat IndicF5** (MIT), **NVIDIA BigVGAN-v2**, and **F5-TTS** — the vocoder is a BigVGAN-v2 derivative; please observe NVIDIA's BigVGAN license terms. Cite *Vāgdhenu* (BibTeX with the technical report).
