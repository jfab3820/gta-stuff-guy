#!/usr/bin/env python3
"""patch_v2.py - turns the v1 render_short.py (playbook appendix) into v2.
Run it once in the folder that holds render_short.py: python3 patch_v2.py
v2 adds: "bg": "drive" (moving neon road, sun on the horizon), "safe": [top, bottom], a flash on each cut.
"""
s = open("render_short.py").read()


def swap(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)


swap("import json, os, subprocess, sys", "import json, os, random, subprocess, sys")
swap("ZOOM = 1.07", '''ZOOM = 1.07
HORIZON = 1400
PERIOD = 20''')
swap("def bg_frame(bg, p):", '''def make_drive_background():
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


def bg_frame(bg, p):''')
swap('''def frame(bg, items, k, p, instant):
    im = bg_frame(bg, p).convert("RGBA")''', '''def frame(base, items, k, instant, flash=0.0):
    im = base.convert("RGBA")''')
swap('''    return im.convert("RGB")


def main():''', '''    im = im.convert("RGB")
    if flash > 0:
        im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), flash)
    return im


def main():''')
swap("    bg = make_background()", '''    global SAFE_TOP, SAFE_BOTTOM
    if "safe" in spec:
        SAFE_TOP, SAFE_BOTTOM = spec["safe"]
    if spec.get("bg") == "drive":
        sky, roads = make_drive_background()
        base = lambda g, total: drive_frame(sky, roads, g)
    else:
        bg = make_background()
        base = lambda g, total: bg_frame(bg, g / total)''')
swap("frame(bg, items, k, (done + k) / total, inst).save(", "frame(base(done + k, total), items, k, inst).save(")
swap("            ff.stdin.write(frame(bg, items, k, (done + k) / total, inst).tobytes())", '''            fl = 0.3 * (1 - k / 5) if (i > 0 and k < 5 and spec.get("flash", True)) else 0.0
            ff.stdin.write(frame(base(done + k, total), items, k, inst, fl).tobytes())''')
open("render_short.py", "w").write(s)
print("render_short.py is now v2")
