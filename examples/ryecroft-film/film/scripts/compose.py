#!/usr/bin/env python3
"""Compose the film's own music, written to the film's bar grid. Nothing is sampled or licensed: every sound is synthesised here.

Reads timing.json (tempo, the drop, the breakdown under the eye-level walk, the pullback and the final hit) and writes music/theme.wav.
D major at the film's tempo. Warm pad, electric-piano stabs, a syncopated bass, a plucked arpeggio with an echo, and a light kit.
Deterministic: the same timing gives the same file.
"""
import json
import math
import os

import numpy as np
from scipy.signal import butter, lfilter

SR = 48000
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(here)
T = json.load(open("timing.json"))
BAR, BEAT, PH, DUR = T["BAR"], T["BEAT"], T["PH"], T["TOTAL"]
N = int((DUR + 3) * SR)
rng = np.random.default_rng(20261127)
BUS = {k: np.zeros((2, N), dtype=np.float32) for k in ("pad", "keys", "bass", "arp", "lead", "kick", "kit", "fx")}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def put(bus, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N or i + len(sig) <= 0:
        return
    sig = sig[: N - i]
    gl, gr = math.cos((pan + 1) * math.pi / 4) * 1.414, math.sin((pan + 1) * math.pi / 4) * 1.414
    BUS[bus][0, i:i + len(sig)] += sig * gain * gl
    BUS[bus][1, i:i + len(sig)] += sig * gain * gr


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na, endpoint=False)[: len(e[:na])]
    seg = e[na:na + nd]; seg[:] = np.linspace(1, s, nd)[: len(seg)]
    if nr and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pad_note(f, dur, detune):
    t = tt(dur + 1.4)
    sig = np.zeros_like(t)
    for c in (-detune, detune):
        ff = f * 2 ** (c / 1200)
        for k in range(1, 7):
            sig += np.sin(2 * math.pi * ff * k * t + k) / k ** 1.7
    return sig * adsr(len(t), 0.7, 0.4, 0.8, 1.4) * 0.5


def keys_note(f, dur=0.9):
    t = tt(dur)
    return np.sin(2 * math.pi * f * t + 1.4 * np.exp(-t / 0.25) * np.sin(2 * math.pi * f * t)) * np.exp(-t / 0.55) * adsr(len(t), 0.004, 0.1, 0.9, 0.08)


def bass_note(f, dur):
    t = tt(dur)
    s = np.sin(2 * math.pi * f * t) + 0.35 * np.sin(4 * math.pi * f * t) + 0.12 * np.sin(6 * math.pi * f * t)
    return np.tanh(1.6 * s) * adsr(len(t), 0.006, 0.12, 0.75, 0.06)


def pluck(f, dur=0.6, bright=2.0):
    t = tt(dur)
    return np.sin(2 * math.pi * f * t + bright * np.exp(-t / 0.12) * np.sin(2 * math.pi * 2 * f * t)) * np.exp(-t / 0.28) * adsr(len(t), 0.002, 0.05, 1.0, 0.05)


def bell(f, dur=4.0):
    t = tt(dur)
    return sum(np.sin(2 * math.pi * f * r * t) * np.exp(-t / d) * a for r, d, a in ((1, 1.6, 1.0), (2.76, 0.9, 0.35), (5.4, 0.5, 0.18))) * adsr(len(t), 0.002, 0.05, 1.0, 0.5)


def kick():
    t = tt(0.32)
    ph = 2 * math.pi * (46 * t + (115 - 46) * 0.035 * (1 - np.exp(-t / 0.035)))
    return np.sin(ph) * np.exp(-t / 0.13) + 0.25 * np.exp(-t / 0.004) * rng.standard_normal(len(t))


def noise(dur, lo=None, hi=None):
    x = rng.standard_normal(int(dur * SR))
    if lo and hi:
        b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
    elif lo:
        b, a = butter(2, lo / (SR / 2), "high")
    elif hi:
        b, a = butter(2, hi / (SR / 2), "low")
    else:
        return x
    return lfilter(b, a, x)


def clap():
    t = tt(0.22)
    e = sum(np.exp(-np.clip(t - d, 0, None) / 0.012) * (t >= d) for d in (0.0, 0.011, 0.023)) * 0.5 + np.exp(-t / 0.07)
    return noise(0.22, 900, 3800) * e * 0.6


def hat(open_=False):
    d = 0.2 if open_ else 0.045
    t = tt(d)
    return noise(d, 7000) * np.exp(-t / (0.07 if open_ else 0.014))


def riser(dur):
    t = tt(dur)
    x = rng.standard_normal(len(t)); y = np.zeros_like(x); acc = 0.0
    a = 0.01 + 0.25 * (t / dur) ** 2
    for i in range(len(x)):                       # a filter that opens as it rises
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y * (t / dur) ** 2 * 2.0


# ---------- harmony ----------
A_SEC = [([62, 66, 69, 76], 38), ([59, 62, 66, 69], 35), ([55, 59, 62, 66], 43), ([57, 61, 64, 71], 45)]      # Dmaj9, Bm7, Gmaj7, Aadd9
B_SEC = [([55, 59, 62, 66], 43), ([57, 61, 64, 69], 45), ([59, 62, 66, 69], 35), ([54, 57, 61, 64], 42)]      # Gmaj7, A, Bm7, F#m7
MOTIF = [[78, None, 81, None, 83, 81, None, 78], [74, None, 78, None, 76, None, 74, None]]

drop_bar = T["DB"] // 4
bd = T.get("breakdown")
bd0, bd1 = (round((bd[0] - PH) / BAR), round((bd[1] - PH) / BAR)) if bd else (10 ** 6, 10 ** 6)
pull_bar = round((T["cues"]["pull"] - PH) / BAR)
fin_bar, end_bar = T["FIN"], T["ENDB"]
kicks = []


def chord_at(b):
    rel = b - drop_bar
    sec = B_SEC if rel >= 0 and (rel // 8) % 3 == 2 else A_SEC
    return sec[b % 4]


for b in range(end_bar):
    t0 = PH + b * BAR
    notes, root = chord_at(b)
    intro, breakdown = b < drop_bar, bd0 <= b < bd1
    outro = b >= fin_bar
    main = not intro and not breakdown and not outro
    rel = b - drop_bar
    last_of_phrase = main and rel % 8 == 7
    # pad: always, swelling through the intro
    pg = (0.35 + 0.65 * b / max(1, drop_bar)) if intro else (1.0 if not breakdown else 1.15)
    for i, m in enumerate(notes):
        put("pad", pad_note(hz(m), BAR, 5 + i), t0, 0.075 * pg, pan=(-0.5, 0.4, -0.2, 0.55)[i])
    # intro: a few plucked notes of the motif
    if intro:
        for step, m in enumerate(MOTIF[b % 2]):
            if m and step % 2 == 0:
                put("lead", pluck(hz(m - 12), 0.9, 1.2), t0 + step * BEAT / 2, 0.10, pan=0.2)
    if main or breakdown:
        # arpeggio with an echo, from four bars after the drop
        if rel >= 4 or breakdown:
            seq = [notes[0], notes[2], notes[1], notes[3], notes[2], notes[3], notes[1], notes[2]]
            for step, m in enumerate(seq):
                ts = t0 + step * BEAT / 2 + (0.03 * BEAT if step % 2 else 0)
                g = 0.085 if breakdown else 0.06
                put("arp", pluck(hz(m + 12), 0.5), ts, g, pan=-0.35)
                for rep in (1, 2, 3):                                  # dotted-eighth echo, bouncing left and right
                    put("arp", pluck(hz(m + 12), 0.5), ts + rep * 0.75 * BEAT, g * 0.42 ** rep, pan=0.6 if rep % 2 else -0.6)
    if main:
        # bass: syncopated around the root
        for beat, dur, m in ((0, 1.2, root), (1.5, 0.45, root + 12), (2.5, 0.9, root), (3.5, 0.45, root + 7)):
            put("bass", bass_note(hz(m), dur * BEAT), t0 + beat * BEAT, 0.30)
        # electric piano on the off-beats
        for beat in (1.5, 3.5) if rel % 2 == 0 else (0.5, 2.5, 3.5):
            for i, m in enumerate(notes):
                put("keys", keys_note(hz(m)), t0 + beat * BEAT, 0.05, pan=(-0.3, 0.3, -0.1, 0.2)[i])
        # the motif, every other eight-bar phrase and through the pullback
        if (rel // 8) % 2 == 1 or b >= pull_bar:
            for step, m in enumerate(MOTIF[b % 2]):
                if m:
                    put("lead", pluck(hz(m), 0.7, 1.6), t0 + step * BEAT / 2, 0.075, pan=0.25)
        # kit
        for beat in (0, 2) + ((3.5,) if rel % 2 == 1 and not last_of_phrase else ()):
            if not (last_of_phrase and beat == 2):
                put("kick", kick(), t0 + beat * BEAT, 0.62); kicks.append(t0 + beat * BEAT)
        if rel >= 2:
            for beat in (1, 3):
                put("kit", clap(), t0 + beat * BEAT, 0.20, pan=0.05)
        for step in range(8):
            sw = 0.035 * BEAT if step % 2 else 0
            put("kit", hat(), t0 + step * BEAT / 2 + sw, 0.10 if step % 2 else 0.065, pan=0.3)
        put("kit", hat(True), t0 + 3.5 * BEAT, 0.07, pan=-0.3)
        if last_of_phrase:                                              # a small fill and a swell into the next phrase
            for q in range(4):
                put("kit", clap(), t0 + (3 + q / 4) * BEAT, 0.07 + 0.03 * q)
            put("fx", riser(BEAT * 2), t0 + 2 * BEAT, 0.10)
    if breakdown:
        for step in range(16):                                          # a shaker keeps time under the walk
            put("kit", hat(), t0 + step * BEAT / 4, 0.022 + 0.018 * (step % 4 == 2), pan=-0.2)
        put("kick", kick(), t0, 0.30); kicks.append(t0)
        if b == bd1 - 1:
            put("fx", riser(BAR), t0, 0.16)
            for q in range(8):
                put("kit", clap(), t0 + (2 + q / 4) * BEAT, 0.05 + 0.02 * q)
    if b == drop_bar - 1:
        put("fx", riser(BAR), t0, 0.18)
    if outro:
        for step in range(8):
            put("kit", hat(), t0 + step * BEAT / 2, 0.05, pan=0.3)
        if b == end_bar - 1:
            put("fx", riser(BAR), t0, 0.14)

# the final hit: D add9, a bell on top and a low thump, left to ring
tE = PH + end_bar * BAR
for i, m in enumerate([50, 57, 62, 66, 69, 76]):
    put("pad", pad_note(hz(m), 3.0, 4 + i), tE, 0.08, pan=(-0.5, 0.5, -0.3, 0.3, -0.1, 0.1)[i])
for m, g in ((74, 0.16), (81, 0.10), (86, 0.07)):
    put("lead", bell(hz(m)), tE, g)
put("kick", kick(), tE, 0.7); put("bass", bass_note(hz(38), 1.6), tE, 0.3)

# ---------- mix: duck the pad, keys and bass under each kick, then glue ----------
duck = np.ones(N, dtype=np.float32)
t = tt(0.4)
shape = 0.42 * np.exp(-t / 0.14)
for k in kicks:
    i = int(k * SR)
    if i < N:
        seg = duck[i:i + len(shape)]
        seg[:] = np.minimum(seg, 1 - shape[: len(seg)])
for name in ("pad", "keys", "bass", "arp"):
    BUS[name] *= duck
b_lp, a_lp = butter(2, 9000 / (SR / 2), "low")
mix = sum(BUS.values())
mix = lfilter(b_lp, a_lp, mix, axis=1)
mix = np.tanh(mix * 1.15) / 1.15
mix *= 0.72 / np.abs(mix).max()
os.makedirs("music", exist_ok=True)
import struct
data = mix.T.astype("<f4").tobytes()
with open("music/theme.wav", "wb") as f:
    f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 3, 2, SR, SR * 8, 8, 32))
    f.write(b"data" + struct.pack("<I", len(data)) + data)
print(f"music/theme.wav: {N / SR:.1f} s at {60 / BEAT:.0f} bpm · drop bar {drop_bar} · breakdown bars {bd0} to {bd1} · pullback bar {pull_bar} · final hit bar {end_bar} · {len(kicks)} kicks")
