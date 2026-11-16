#!/usr/bin/env python3
"""make_music.py - original synth bed for a Short (no samples, nothing licensed).

Usage: python3 make_music.py out.wav SECONDS [CUT_SECONDS,CUT_SECONDS,...] [sfx]
Am - F - C - G at 100 BPM: pad, plucked arp with echo, bass pulse, soft kick, light hat.
Deterministic. Mux onto a video with:
  ffmpeg -i video.mp4 -i out.wav -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart final.mp4
"""
import sys, wave
import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
BPM = 100
BEAT = 60.0 / BPM
BAR = 4 * BEAT
CHORDS = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]   # Am, F, C/G, G
ROOTS = [45, 41, 48, 43]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def saw(f, t, harmonics=8):
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if f * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * f * k * t) / k
    return out


def add(buf, start, sig):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def lowpass(x, cutoff):
    b, a = butter(2, cutoff / (SR / 2), "low")
    return lfilter(b, a, x)


def highpass(x, cutoff):
    b, a = butter(2, cutoff / (SR / 2), "high")
    return lfilter(b, a, x)


def main():
    out, dur = sys.argv[1], float(sys.argv[2])
    n = int(SR * dur)
    L, R = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(6)
    bars = int(np.ceil(dur / BAR))
    padL, padR, arpL, arpR, bass, kick, hat = (np.zeros(n) for _ in range(7))
    for b in range(bars):
        t0 = b * BAR
        chord, root = CHORDS[b % 4], ROOTS[b % 4]
        # pad: one bar, slow in and out, detuned left/right
        tb = np.arange(int(SR * BAR)) / SR
        env = np.minimum(1, tb / 0.35) * np.minimum(1, (BAR - tb) / 0.35)
        for m in chord:
            add(padL, t0, saw(hz(m) * 1.003, tb) * env)
            add(padR, t0, saw(hz(m) * 0.997, tb) * env)
        # arp: sixteenth notes, plucked
        notes = [chord[0], chord[1], chord[2], chord[0] + 12, chord[2], chord[1], chord[0] + 12, chord[2]]
        tp = np.arange(int(SR * 0.4)) / SR
        for s in range(16):
            f = hz(notes[s % 8] + 12)
            pl = (np.sin(2 * np.pi * f * tp) + np.sin(2 * np.pi * 3 * f * tp) / 9) * np.exp(-tp / 0.09)
            pan = 0.35 if s % 2 else 0.65
            add(arpL, t0 + s * BEAT / 4, pl * pan)
            add(arpR, t0 + s * BEAT / 4, pl * (1 - pan))
        # bass: eighth-note pulse on the root
        tq = np.arange(int(SR * BEAT / 2)) / SR
        for s in range(8):
            add(bass, t0 + s * BEAT / 2, saw(hz(root), tq, 5) * np.exp(-tq / 0.16))
        # kick on each beat, hat on the off-beats
        tk = np.arange(int(SR * 0.3)) / SR
        fk = 50 + 70 * np.exp(-tk / 0.03)
        kk = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-tk / 0.11)
        th = np.arange(int(SR * 0.06)) / SR
        for s in range(4):
            add(kick, t0 + s * BEAT, kk)
            add(hat, t0 + s * BEAT + BEAT / 2, rng.standard_normal(len(th)) * np.exp(-th / 0.012))
    # echo on the arp (dotted eighth)
    d = int(SR * BEAT * 0.75)
    for buf in (arpL, arpR):
        for _ in range(3):
            buf[d:] += 0.35 * buf[:-d].copy()
    padL, padR = lowpass(padL, 1700), lowpass(padR, 1700)
    bass = lowpass(bass, 900)
    hat = highpass(hat, 6000)
    L = 0.10 * padL + 0.24 * arpL + 0.30 * bass + 0.55 * kick + 0.05 * hat
    R = 0.10 * padR + 0.24 * arpR + 0.30 * bass + 0.55 * kick + 0.05 * hat
    sfx_only = len(sys.argv) > 4 and sys.argv[4] == "sfx"     # cut effects only, for when the music is added elsewhere
    if sfx_only:
        L, R = np.zeros(n), np.zeros(n)
    # optional scene-cut effects: a short noise riser into each cut, then a low thump on it
    cuts = [float(c) for c in sys.argv[3].split(",")] if len(sys.argv) > 3 else []
    for c in cuts:
        tr = np.arange(int(SR * 0.35)) / SR
        riser = highpass(rng.standard_normal(len(tr)), 900) * (tr / 0.35) ** 2 * 0.30
        tt = np.arange(int(SR * 0.45)) / SR
        thump = np.sin(2 * np.pi * 52 * tt) * np.exp(-tt / 0.16) * 0.55
        for buf in (L, R):
            add(buf, c - 0.35, riser)
            add(buf, c, thump)
    mix = np.stack([L, R], axis=1)
    mix = np.tanh(mix * 1.2)
    mix *= (0.4 if sfx_only else 0.7) / np.max(np.abs(mix))
    fade = int(SR * 0.7)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix[:220] *= np.linspace(0, 1, 220)[:, None]
    assert np.isfinite(mix).all()
    pcm = (mix * 32767).astype("<i2")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote %s  %.1f s  peak %.2f  rms %.3f" % (out, dur, np.max(np.abs(mix)), np.sqrt(np.mean(mix ** 2))))


if __name__ == "__main__":
    main()
