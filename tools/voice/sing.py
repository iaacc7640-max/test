"""Make the sung vocal track (vocals.mp3) for the music video.

Each word of song.js is spoken by Meta's MMS-TTS Marathi voice, then reshaped
with the WORLD vocoder: vowels are stretched to the word's beats, the pitch is
set to the word's melody notes (with a little vibrato) and the formants are
raised for a brighter, child-like voice. Words are placed on the beat grid and
given a light reverb.

Run from this folder:  uv run python sing.py
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
import torch
from scipy.signal import fftconvolve, resample_poly
from transformers import AutoTokenizer, VitsModel

ROOT = Path(__file__).resolve().parents[2]
TTS_RATE, OUT_RATE, FRAME_MS = 16000, 44100, 5.0
FORMANT_SHIFT = 1.15   # >1 = brighter, younger-sounding voice
SONG_SECONDS = 58      # must match DUR in index.html


def load_song():
    text = (ROOT / "song.js").read_text(encoding="utf-8")
    body = text.split("window.SONG =", 1)[1].strip().rstrip(";")
    return json.loads(body)


def speak(model, tok, word):
    torch.manual_seed(1)
    with torch.no_grad():
        y = model(**tok(word, return_tensors="pt")).waveform[0].numpy().astype(np.float64)
    # trim leading/trailing silence
    env = np.convolve(np.abs(y), np.ones(160) / 160, mode="same")
    on = np.where(env > env.max() * 0.04)[0]
    return y[max(on[0] - 80, 0): on[-1] + 80]


def stretch_map(voiced, n_out):
    """Source frame position for every output frame, stretching voiced frames only."""
    n_v = voiced.sum()
    n_u = len(voiced) - n_v
    k = (n_out - n_u) / n_v if n_v and n_out > n_u else n_out / len(voiced)
    weights = np.where(voiced, k, 1.0) if n_v and n_out > n_u else np.full(len(voiced), k)
    edges = np.concatenate([[0], np.cumsum(weights)])
    return np.interp(np.arange(n_out) + 0.5, edges, np.arange(len(voiced) + 1)) - 0.5


def sing(x, notes, seconds):
    f0, t = pw.harvest(x, TTS_RATE, frame_period=FRAME_MS, f0_floor=70, f0_ceil=500)
    sp = pw.cheaptrick(x, f0, t, TTS_RATE)
    ap = pw.d4c(x, f0, t, TTS_RATE)

    n_out = max(int(seconds * 1000 / FRAME_MS), 4)
    pos = np.clip(stretch_map(f0 > 0, n_out), 0, len(f0) - 1)
    lo = np.floor(pos).astype(int)
    hi = np.minimum(lo + 1, len(f0) - 1)
    w = (pos - lo)[:, None]
    sp2 = sp[lo] * (1 - w) + sp[hi] * w
    ap2 = ap[lo] * (1 - w) + ap[hi] * w
    voiced = f0[np.rint(pos).astype(int)] > 0

    # target pitch: notes spread evenly across the word, smoothed into gentle glides
    seg = np.minimum((np.arange(n_out) * len(notes)) // n_out, len(notes) - 1)
    midi = np.array(notes, dtype=float)[seg]
    midi = np.convolve(np.pad(midi, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    tsec = np.arange(n_out) * FRAME_MS / 1000
    midi += 0.25 * np.sin(2 * np.pi * 5.5 * tsec) * np.clip((tsec - 0.15) / 0.2, 0, 1)
    f0_new = np.where(voiced, 440 * 2 ** ((midi - 69) / 12), 0.0)

    # raise formants by warping the spectral envelope's frequency axis
    bins = np.arange(sp2.shape[1])
    src = bins / FORMANT_SHIFT
    sp2 = np.array([np.interp(src, bins, row) for row in sp2])

    y = pw.synthesize(f0_new, np.ascontiguousarray(sp2), np.ascontiguousarray(ap2), TTS_RATE, FRAME_MS)
    fade = int(0.012 * TTS_RATE)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade * 3:] *= np.linspace(1, 0, fade * 3)
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.12


def reverb(mono, seed):
    rng = np.random.default_rng(seed)
    n = int(1.1 * OUT_RATE)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.25 * OUT_RATE))
    ir[0] = 0
    wet = fftconvolve(mono, ir)[: len(mono)]
    return wet / (np.abs(wet).max() + 1e-9) * np.abs(mono).max()


def main():
    song = load_song()
    beat = 60 / song["bpm"]
    intro = song["intro_beats"] * beat
    model = VitsModel.from_pretrained("facebook/mms-tts-mar")
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-mar")
    model.config.noise_scale = 0.4

    track = np.zeros(int(SONG_SECONDS * OUT_RATE))
    cache = {}
    for i, line in enumerate(song["lines"]):
        for word, start, length, notes in line["words"]:
            if word not in cache:
                cache[word] = speak(model, tok, word)
            y = sing(cache[word], notes, length * beat * 0.94)
            y = resample_poly(y, 441, 160)
            at = int((intro + (8 * i + start) * beat - 0.03) * OUT_RATE)
            track[at: at + len(y)] += y[: len(track) - at]
            print(f"line {i + 1:2d}  {word}")

    left = track + 0.16 * reverb(track, 1)
    right = track + 0.16 * reverb(track, 2)
    stereo = np.stack([left, right], axis=1)
    stereo *= 0.9 / np.abs(stereo).max()

    wav = Path(__file__).with_name("vocals.wav")
    sf.write(wav, stereo, OUT_RATE)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "160k", str(ROOT / "vocals.mp3")], check=True)
    print("wrote", ROOT / "vocals.mp3")


if __name__ == "__main__":
    main()
