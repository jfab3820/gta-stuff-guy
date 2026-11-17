#!/usr/bin/env python3
"""render_short.py - text-forward vertical Short renderer (1080x1920, 30 fps, no audio).

Usage:
  python3 render_short.py spec.json out.mp4            # full render
  python3 render_short.py spec.json out.mp4 --stills D # QC stills only (look at these first)

Spec: {"scenes": [{"dur": seconds, "instant": bool, "els": [element, ...]}, ...]}
Optional host layer (see host.py): "host": {"assets": "assets/host", "w": 900, "top": 1030} plus
"voice": {"lines": [{"start": s, "dur": s, "text": "..."}]} at the top level. Each scene then takes
"host": "talk" (default), "none", or {"clip": "path.mp4", "from": seconds, "w": 1080, "top": 580}.
A scene can carry its own "safe": [top, bottom].
Elements (stacked top to bottom, centred in the safe area):
  {"type":"line","text":"PLAIN *HIGHLIGHT*","size":118,"font":"bold|med","hl":"yellow|cyan|pink","at":frame}
  {"type":"tag","text":"SMALL LABEL","at":frame}
  {"type":"chip","text":"BIG PILL","size":88,"at":frame}
  {"type":"row","label":"LEFT","value":"RIGHT","hl":true,"at":frame}
  {"type":"gap","h":40}
"at" = frame (within the scene) the element enters. Scene 1 should set "instant": true
so the hook is fully on screen at frame 0 (retention rule).
"""
import json, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 250, 1420      # Shorts UI covers the rest
MAX_W = 880
GAP = 22
ANIM = 10                               # entrance length in frames
FONTS = {
    "bold": "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "med": "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
}
COL = {
    "white": (255, 255, 255), "yellow": (255, 214, 10), "cyan": (76, 201, 240),
    "pink": (255, 92, 168), "ink": (11, 2, 33),
}
ZOOM = 1.07
HORIZON = 1400                          # drive background: where the road meets the sky
PERIOD = 20                             # drive background: frames per grid-line spacing


def font(kind, size):
    return ImageFont.truetype(FONTS.get(kind, FONTS["bold"]), size)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def make_background():
    bw, bh = int(W * ZOOM), int(H * ZOOM)
    stops = [(0.00, (9, 2, 28)), (0.42, (30, 8, 74)), (0.68, (92, 20, 130)),
             (0.86, (214, 36, 120)), (1.00, (255, 140, 30))]
    col = Image.new("RGB", (1, bh))
    px = col.load()
    for y in range(bh):
        t = y / (bh - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                px[0, y] = lerp(c0, c1, (t - t0) / (t1 - t0))
                break
    bg = col.resize((bw, bh))
    # striped sun, low in frame (sits behind the Shorts UI, clear of the text area)
    r = int(290 * ZOOM)
    cx, cy = bw // 2, int(bh * 0.905)
    sun = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    grad = Image.new("RGB", (1, 2 * r))
    gp = grad.load()
    for y in range(2 * r):
        gp[0, y] = lerp((255, 226, 90), (255, 70, 150), y / (2 * r - 1))
    grad = grad.resize((2 * r, 2 * r))
    mask = Image.new("L", (2 * r, 2 * r), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    y, band, cut = int(r * 0.95), 46, 8
    while y < 2 * r:
        md.rectangle((0, y, 2 * r, y + cut), fill=0)
        y += band
        cut += 6
        band = max(30, band - 2)
    sun.paste(grad, (cx - r, cy - r), mask)
    glow = sun.filter(ImageFilter.GaussianBlur(60))
    bg = Image.alpha_composite(bg.convert("RGBA"), glow)
    bg = Image.alpha_composite(bg, sun)
    # darken the text area for contrast
    shade = Image.new("L", (1, bh))
    sp = shade.load()
    for y in range(bh):
        t = y / (bh - 1)
        sp[0, y] = int(150 * max(0.0, 1 - t / 0.74))
    shade = shade.resize((bw, bh))
    bg = Image.composite(Image.new("RGBA", (bw, bh), (5, 0, 18, 255)), bg, shade)
    return bg.convert("RGB")


def make_drive_background():
    """Night-drive look: starry sky, striped sun on the horizon, neon grid road scrolling toward the viewer.
    Returns (sky RGB image, PERIOD road strips that loop)."""
    stops = [(0.00, (7, 2, 24)), (0.45, (24, 7, 66)), (0.75, (88, 18, 128)), (1.00, (226, 52, 128))]
    col = Image.new("RGB", (1, HORIZON))
    px = col.load()
    for y in range(HORIZON):
        t = y / (HORIZON - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                px[0, y] = lerp(c0, c1, (t - t0) / (t1 - t0))
                break
    sky = Image.new("RGB", (W, H), (6, 1, 20))
    sky.paste(col.resize((W, HORIZON)), (0, 0))
    d = ImageDraw.Draw(sky)
    rng = random.Random(6)
    for _ in range(150):
        x, y = rng.randrange(W), rng.randrange(int(HORIZON * 0.6))
        b = rng.randrange(110, 255)
        r = rng.choice([1, 1, 1, 2])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(b, b, min(255, b + 25)))
    r = 215
    sun = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("RGB", (1, 2 * r))
    gp = grad.load()
    for y in range(2 * r):
        gp[0, y] = lerp((255, 226, 90), (255, 70, 150), min(1.0, y / (r - 1)))
    grad = grad.resize((2 * r, 2 * r))
    mask = Image.new("L", (2 * r, 2 * r), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    y, band, cut = int(r * 0.45), 30, 4
    while y < r:
        md.rectangle((0, y, 2 * r, y + cut), fill=0)
        y += band
        cut += 3
        band = max(20, band - 2)
    md.rectangle((0, r, 2 * r, 2 * r), fill=0)
    sun.paste(grad, (W // 2 - r, HORIZON - r), mask)
    glow = sun.filter(ImageFilter.GaussianBlur(45))
    sky = Image.alpha_composite(Image.alpha_composite(sky.convert("RGBA"), glow), sun).convert("RGB")
    fh = H - HORIZON
    fade = Image.new("L", (1, fh))
    fp = fade.load()
    for y in range(fh):
        fp[0, y] = int(255 * min(1.0, 0.18 + 1.4 * y / fh))
    fade = fade.resize((W, fh))
    roads = []
    for p in range(PERIOD):
        lines = Image.new("RGBA", (W, fh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(lines)
        for i in range(-16, 17):
            fd.line((W / 2 + i * 5, 0, W / 2 + i * 210, fh), fill=(255, 70, 205, 255), width=3)
        for k in range(1, 40):
            z = k - p / PERIOD
            y = fh / z
            if y < fh + 6:
                fd.line((0, y, W, y), fill=(90, 225, 255, 255), width=max(2, min(7, int(7 / z))))
        lines.putalpha(Image.composite(lines.getchannel("A"), Image.new("L", (W, fh), 0), fade))
        road = Image.new("RGBA", (W, fh), (9, 2, 28, 255))
        road.alpha_composite(lines.filter(ImageFilter.GaussianBlur(7)))
        road.alpha_composite(lines)
        roads.append(road.convert("RGB"))
    return sky, roads


def drive_frame(sky, roads, g):
    im = sky.copy()
    im.paste(roads[g % PERIOD], (0, HORIZON))
    return im


def bg_frame(bg, p):
    """p in 0..1 across the whole video: slow push-in."""
    cw = int(bg.width / (1 + (ZOOM - 1) * p))
    ch = int(bg.height / (1 + (ZOOM - 1) * p))
    x0 = (bg.width - cw) // 2
    y0 = (bg.height - ch) // 2
    return bg.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


def segs(text):
    out, hl = [], False
    for part in text.split("*"):
        if part:
            out.append((part, hl))
        hl = not hl
    return out


def el_line(e):
    kind, size = e.get("font", "bold"), e.get("size", 100)
    plain = e["text"].replace("*", "")
    while size > 30 and font(kind, size).getlength(plain) > MAX_W:
        size -= 2
    f = font(kind, size)
    stroke = max(4, size // 16) if kind == "bold" else max(3, size // 20)
    asc, desc = f.getmetrics()
    w = int(f.getlength(plain)) + 2 * stroke + 24
    h = asc + desc + 2 * stroke
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base = COL[e.get("color", "white")]
    hlc = COL[e.get("hl", "yellow")]
    # soft shadow
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.text((12 + stroke, stroke + 6), plain, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    x = 12 + stroke
    for part, is_hl in segs(e["text"]):
        d.text((x, stroke), part, font=f, fill=hlc if is_hl else base,
               stroke_width=stroke, stroke_fill=COL["ink"])
        x += f.getlength(part)
    return img


def pill(text, size, bg, fg, padx, pady, kind="bold"):
    while size > 28 and font(kind, size).getlength(text) + 2 * padx > MAX_W:
        size -= 2
    f = font(kind, size)
    asc, desc = f.getmetrics()
    w = int(f.getlength(text)) + 2 * padx
    h = asc + desc + 2 * pady
    img = Image.new("RGBA", (w + 16, h + 20), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((8, 12, 8 + w, 12 + h), radius=h // 2, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 4, 8 + w, 4 + h), radius=h // 2, fill=bg)
    d.text((8 + padx, 4 + pady), text, font=f, fill=fg)
    return img


def el_row(e):
    rw, rh = 880, 124
    img = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    hl = e.get("hl", False)
    d.rounded_rectangle((0, 0, rw - 1, rh - 1), radius=26, fill=(11, 2, 33, 214),
                        outline=COL["yellow"] + (255,) if hl else (255, 255, 255, 70), width=4 if hl else 2)
    fl, fv = font("med", 50), font("bold", 60)
    al, dl = fl.getmetrics()
    av, dv = fv.getmetrics()
    d.text((38, (rh - al - dl) // 2), e["label"], font=fl, fill=(235, 230, 250))
    vw = fv.getlength(e["value"])
    d.text((rw - 38 - vw, (rh - av - dv) // 2), e["value"], font=fv, fill=COL["yellow"] if hl else COL["white"])
    return img


def build(e):
    t = e["type"]
    if t == "line":
        return el_line(e)
    if t == "tag":
        return pill(e["text"], e.get("size", 44), COL["cyan"], COL["ink"], 34, 12)
    if t == "chip":
        return pill(e["text"], e.get("size", 88), COL["yellow"], COL["ink"], 46, 18)
    if t == "row":
        return el_row(e)
    raise ValueError("unknown element type: " + t)


def layout(scene):
    items, total, prev = [], 0, None
    for e in scene["els"]:
        if e["type"] == "gap":
            total += e.get("h", 40)
            prev = "gap"
            continue
        img = build(e)
        if items:
            if e["type"] == "row":
                dflt = 10
            elif e["type"] == "line" and prev == "line":
                dflt = -int(0.14 * e.get("size", 100))   # stack text lines tight
            else:
                dflt = GAP
            total += e.get("space", dflt)
        items.append([img, total, e.get("at", 0)])
        total += img.height
        prev = e["type"]
    st, sb = scene.get("safe", (SAFE_TOP, SAFE_BOTTOM))
    if total > sb - st:
        raise SystemExit("scene too tall for the safe area: %d px (room %d)" % (total, sb - st))
    top = st + (sb - st - total) // 2
    return [(img, top + y, at) for img, y, at in items]


def ease(t):
    return 1 - (1 - t) ** 3


def frame(base, items, k, instant, flash=0.0):
    im = base.convert("RGBA")
    for img, y, at in items:
        if instant:
            a, dy = 1.0, 0
        else:
            t = (k - at) / ANIM
            if t <= 0:
                continue
            a = ease(min(1.0, t))
            dy = int(36 * (1 - a))
        x = (W - img.width) // 2
        if a >= 0.999:
            im.alpha_composite(img, (x, y + dy))
        else:
            tmp = img.copy()
            tmp.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
            im.alpha_composite(tmp, (x, y + dy))
    im = im.convert("RGB")
    if flash > 0:
        im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), flash)
    return im


def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    stills = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--stills" else None
    global SAFE_TOP, SAFE_BOTTOM
    if "safe" in spec:
        SAFE_TOP, SAFE_BOTTOM = spec["safe"]
    if spec.get("bg") == "drive":
        sky, roads = make_drive_background()
        base = lambda g, total: drive_frame(sky, roads, g)
    else:
        bg = make_background()
        base = lambda g, total: bg_frame(bg, g / total)
    counts = [int(round(s["dur"] * FPS)) for s in spec["scenes"]]
    total = sum(counts)
    host = None
    if spec.get("host"):
        from host import HostLayer
        host = HostLayer(spec, counts)
        plain = base
        base = None
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "_scenes")
    os.makedirs(work, exist_ok=True)
    done, files = 0, []
    for i, s in enumerate(spec["scenes"]):
        items = layout(s)
        n = counts[i]
        inst = bool(s.get("instant"))
        if stills:
            os.makedirs(stills, exist_ok=True)
            picks = [0, n - 1] if i == 0 else [n - 1]
            if host:
                picks = sorted(set(picks + [n // 3, (2 * n) // 3]))
            for k in picks:
                b = host.apply(plain(done + k, total), s, i, k, done + k, sequential=False) if host else base(done + k, total)
                frame(b, items, k, inst).save(os.path.join(stills, "s%d_f%03d.png" % (i + 1, k)))
            done += n
            continue
        tmp = os.path.join(work, "scene%d.tmp.mp4" % (i + 1))
        fin = os.path.join(work, "scene%d.mp4" % (i + 1))
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for k in range(n):
            fl = 0.3 * (1 - k / 5) if (i > 0 and k < 5 and spec.get("flash", True)) else 0.0
            b = host.apply(plain(done + k, total), s, i, k, done + k) if host else base(done + k, total)
            ff.stdin.write(frame(b, items, k, inst, fl).tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise SystemExit("ffmpeg failed on scene %d" % (i + 1))
        os.replace(tmp, fin)
        files.append(fin)
        done += n
        print("scene %d: %d frames" % (i + 1, n), flush=True)
    if stills:
        print("stills in", stills)
        return
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for p in files:
            f.write("file '%s'\n" % p)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                           "-c", "copy", "-movflags", "+faststart", out])
    print("wrote %s (%d frames, %.1f s)" % (out, total, total / FPS))


if __name__ == "__main__":
    main()
