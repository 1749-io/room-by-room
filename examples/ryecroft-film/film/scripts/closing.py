"""Extend assets/mix.wav under the closing card: the film's final chord (D add9) once more, softly, then a fade.

Run after scripts/mix.py. The body of the mix (everything up to timing TOTAL) is copied sample for sample; only the
added CLOSE seconds are new. The chord uses the pad and bell voices of scripts/compose.py."""
import json
import math
import os
import struct

import numpy as np
from scipy.signal import butter, lfilter

SR = 48000
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open("timing.json"))
TOTAL, CLOSE = T["TOTAL"], T["CLOSE"]


def read_f32(path):
    b = open(path, "rb").read()
    i = b.index(b"fmt "); fmt, ch, sr, _, _, bits = struct.unpack("<HHIIHH", b[i + 8:i + 24])
    assert (fmt, ch, sr, bits) in ((3, 2, SR, 32), (65534, 2, SR, 32)), (fmt, ch, sr, bits)
    j = b.index(b"data"); n = struct.unpack("<I", b[j + 4:j + 8])[0]
    raw = b[j + 8:j + 8 + n] if 0 < n <= len(b) - j - 8 else b[j + 8:]
    return np.frombuffer(raw[: len(raw) // 8 * 8], dtype="<f4").reshape(-1, 2).copy()


body = read_f32("assets/mix.wav")
n_body = round(TOTAL * SR)
assert abs(len(body) - n_body) <= 2, f"assets/mix.wav is {len(body) / SR:.3f} s, expected the {TOTAL} s body: run scripts/mix.py first"
body = body[:n_body]
tt = lambda dur: np.arange(int(dur * SR)) / SR
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def pad_note(f, dur, detune):                  # the pad voice of compose.py with a slower attack and a longer release
    t = tt(dur)
    sig = np.zeros_like(t)
    for c in (-detune, detune):
        ff = f * 2 ** (c / 1200)
        for k in range(1, 7):
            sig += np.sin(2 * math.pi * ff * k * t + k) / k ** 1.7
    env = np.minimum(1, t / 0.9) * np.minimum(1, (dur - t) / 2.4)
    return sig * env * 0.5


def bell(f, dur=3.6):                          # the bell voice of compose.py
    t = tt(dur)
    env = np.minimum(1, t / 0.002) * np.minimum(1, (dur - t) / 0.5)
    return sum(np.sin(2 * math.pi * f * r * t) * np.exp(-t / d) * a for r, d, a in ((1, 1.6, 1.0), (2.76, 0.9, 0.35), (5.4, 0.5, 0.18))) * env


n_tail = round(CLOSE * SR)
tail = np.zeros((n_tail, 2), dtype=np.float64)


def put(sig, at, gain, pan):
    i = int(at * SR); sig = sig[: n_tail - i]
    tail[i:i + len(sig), 0] += sig * gain * math.sqrt((1 - pan) / 2)
    tail[i:i + len(sig), 1] += sig * gain * math.sqrt((1 + pan) / 2)


for i, m in enumerate([50, 57, 62, 66, 69, 76]):
    put(pad_note(hz(m), CLOSE - 0.25, 4 + i), 0.15, 1.0, (-0.5, 0.5, -0.3, 0.3, -0.1, 0.1)[i])
put(bell(hz(74)), 0.45, 0.5, 0.0)
b_lp, a_lp = butter(2, 5000 / (SR / 2), "low")
tail = lfilter(b_lp, a_lp, tail, axis=0)
tail *= 0.16 / np.abs(tail).max()             # soft: about 16 dB under full scale, well under the final hit
tail[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
out = np.concatenate([body, tail.astype("<f4")]).astype("<f4")
data = out.tobytes()
with open("assets/mix.wav", "wb") as f:
    f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 3, 2, SR, SR * 8, 8, 32))
    f.write(b"data" + struct.pack("<I", len(data)) + data)
print(f"assets/mix.wav: {len(out) / SR:.2f} s = {TOTAL} s body unchanged + {CLOSE} s closing chord, tail peak {np.abs(tail).max():.3f}")
