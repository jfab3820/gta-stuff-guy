#!/usr/bin/env python3
"""host.py - the GTA Stuff Guy host layer for render_short.py.

Two ways to show the host, both keyed off flat green:
  talk: a puppet built from four stills in assets/host (mouth closed, half, open; eyes closed).
        Only the mouth and eye regions change, so the rest of the face stays still.
        The mouth follows the voice line start times and the words of each line. This is
        timed flapping, not true lip sync: the renderer cannot hear the voice file.
  clip: a green-screen motion clip (for example a Higgsfield motion transfer), keyed per frame.
"""
import math, random, re, subprocess
import numpy as np
from PIL import Image, ImageFilter

W, H, FPS = 1080, 1920, 30


def key_green(rgb):
    """rgb uint8 (h,w,3) on flat green -> RGBA uint8. Keys on how far green exceeds red and blue,
    so the teal jacket (green about equal to blue) stays solid and keeps its colour."""
    a = rgb.astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = g - np.maximum(r, b)
    t = np.clip((d - 22.0) / (85.0 - 22.0), 0.0, 1.0)
    alpha = 1.0 - t * t * (3 - 2 * t)
    g2 = np.minimum(g, np.maximum(r, b) + 6.0)          # despill: only pixels where green dominates
    out = np.dstack([r, g2, b, alpha * 255.0])
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def _soft_mask(size, box, blur):
    m = Image.new("L", size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(m).ellipse(box, fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)[..., None] / 255.0


def build_puppet(d, width):
    """Returns {(mouth 0..2, blink 0..1): RGBA PIL image at `width`} from the four stills."""
    def load(name):
        return np.asarray(Image.open(d + "/" + name).convert("RGB").resize((2048, 2048), Image.LANCZOS)).astype(np.float32)
    closed, half, opened, blink = (load(n) for n in
                                   ("host_closed.jpg", "host_half.jpg", "host_open.jpg", "host_blink_src.jpg"))
    size = (2048, 2048)
    m_half = _soft_mask(size, (700, 900, 1380, 1260), 34)       # lips and moustache
    m_open = _soft_mask(size, (610, 850, 1470, 1710), 46)       # whole lower face: the jaw drops
    m_eyes = _soft_mask(size, (730, 575, 1350, 755), 20)
    mouths = [closed, closed * (1 - m_half) + half * m_half, closed * (1 - m_open) + opened * m_open]
    out = {}
    for mi, face in enumerate(mouths):
        for bi in (0, 1):
            im = face * (1 - m_eyes) + blink * m_eyes if bi else face
            rgba = Image.fromarray(key_green(np.clip(im, 0, 255).astype(np.uint8)), "RGBA")
            out[(mi, bi)] = rgba.resize((width, width), Image.LANCZOS)
    return out


_NUM = {"6": "six", "24": "twenty four", "11": "eleven", "9": "nine", "30": "thirty", "12": "twelve",
        "10": "ten", "8": "eight", "7": "seven", "5": "five", "4": "four", "3": "three", "2": "two", "1": "one"}


def _syllables(word):
    w = re.sub(r"[^a-z0-9]", "", word.lower())
    if not w:
        return 0
    if w in ("gta", "pm", "am", "et", "ps5"):
        return len(w)
    if w.isdigit():
        w = _NUM.get(w, "x" * 0 + "one two")
    w = w.replace("-", " ")
    return max(1, len(re.findall(r"[aeiouy]+", re.sub(r"e$", "", w))) or 1)


def mouth_track(lines, total_frames):
    """lines: [{"start": s, "dur": s, "text": str}] -> mouth state per frame (0 closed, 1 half, 2 open)."""
    track = [0] * total_frames
    for ln in lines:
        t0, t1 = ln["start"] + 0.06, ln["start"] + ln["dur"] - 0.28
        units = []                                   # (kind, weight): syllable or pause
        for tok in ln["text"].replace("-", " ").split():
            for _ in range(_syllables(tok)):
                units.append(("s", 1.0))
            if tok[-1] in ".?!":
                units.append(("p", 2.2))
            elif tok[-1] in ",:;":
                units.append(("p", 1.0))
            else:
                units.append(("p", 0.18))
        while units and units[-1][0] == "p":
            units.pop()
        scale = (t1 - t0) / sum(w for _, w in units)
        t, strong = t0, True
        for kind, w in units:
            dur = w * scale
            if kind == "s":
                a, b = int(round(t * FPS)), int(round((t + dur) * FPS))
                n = max(1, b - a)
                for j in range(n):
                    p = (j + 0.5) / n
                    peak = 2 if strong else 1
                    v = peak if 0.25 <= p <= 0.75 else 1
                    if a + j < total_frames:
                        track[a + j] = v
                strong = not strong
            else:
                strong = True
            t += dur
    return track


def blink_track(total_frames, seed=11):
    rng = random.Random(seed)
    track = [0] * total_frames
    f = int(rng.uniform(1.2, 2.2) * FPS)
    while f < total_frames:
        for j in range(3):
            if f + j < total_frames:
                track[f + j] = 1
        f += int(rng.uniform(2.4, 4.6) * FPS)
    return track


class ClipReader:
    """Reads a green-screen clip from `start` seconds at 30 fps, scaled to `width`, keyed, frame by frame."""

    def __init__(self, path, start, width, rows):
        self.w, self.rows = width, rows
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-ss", "%.3f" % start, "-i", path,
             "-vf", "fps=%d,scale=%d:-2:flags=lanczos,crop=%d:%d:0:0" % (FPS, width, width, rows),
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.last = None

    def next(self):
        buf = self.proc.stdout.read(self.w * self.rows * 3)
        if len(buf) == self.w * self.rows * 3:
            rgb = np.frombuffer(buf, np.uint8).reshape(self.rows, self.w, 3)
            self.last = Image.fromarray(key_green(rgb), "RGBA")
        return self.last

    def close(self):
        self.proc.kill()


class HostLayer:
    def __init__(self, spec, counts):
        h = spec["host"]
        self.cfg = h
        self.total = sum(counts)
        self.w = h.get("w", 900)
        self.top = h.get("top", 1030)
        self.puppet = build_puppet(h.get("assets", "assets/host"), self.w)
        self.mouth = mouth_track(spec.get("voice", {}).get("lines", []), self.total)
        self.blink = blink_track(self.total)
        self.reader, self.reader_scene = None, None

    def _talk(self, g):
        t = g / FPS
        im = self.puppet[(self.mouth[g], self.blink[g])]
        ang = 0.7 * math.sin(2 * math.pi * t / 3.7)
        dy = 5 * math.sin(2 * math.pi * t / 2.6) + (3 if self.mouth[g] == 2 else 0)
        dx = 4 * math.sin(2 * math.pi * t / 5.3)
        im = im.rotate(ang, resample=Image.BICUBIC, center=(self.w / 2, self.w * 0.95))
        return im, (int(round((W - self.w) / 2 + dx)), int(round(self.top + dy)))

    def apply(self, base, scene, i, k, g, sequential=True):
        mode = scene.get("host", "talk")
        if mode == "none":
            return base
        im = base.convert("RGBA")
        if mode == "talk":
            if self.reader:
                self.reader.close()
                self.reader, self.reader_scene = None, None
            layer, pos = self._talk(g)
            im.alpha_composite(layer, pos)
            return im.convert("RGB")
        w, top = mode.get("w", W), mode.get("top", 580)
        rows = min(H - top, int(w * 16 / 9))
        if sequential:
            if self.reader_scene != i:
                if self.reader:
                    self.reader.close()
                self.reader, self.reader_scene = ClipReader(mode["clip"], mode.get("from", 0.0), w, rows), i
            layer = self.reader.next()
        else:                                           # stills: seek straight to this frame
            r = ClipReader(mode["clip"], mode.get("from", 0.0) + k / FPS, w, rows)
            layer = r.next()
            r.close()
        if layer is not None:
            im.alpha_composite(layer, ((W - w) // 2, top))
        return im.convert("RGB")
