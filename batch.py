#!/usr/bin/env python3
"""batch.py - make a day's Shorts in one run: one voice request, local mix, checks.

  python3 batch.py lines  batches/2026-11-19.json
      Prints every voice line of every Short, in order, as JSON. Pass that list as
      `scriptLines` to vidiq_voiceover_generate (one request, billed on the combined length)
      and save the tool's result to batches/2026-11-19.voice.json.

  python3 batch.py build  batches/2026-11-19.json batches/2026-11-19.voice.json [--stills]
      Downloads the line audio, times each spec to its own voice, renders the video
      (render_short.py), mixes voice and the channel music, sets loudness to -15 LUFS,
      checks the result and writes out/<id>.mp4 plus batches/<date>.report.json.
      --stills renders QC stills only, into work/<id>_stills/.

Batch file:
  {"date": "2026-11-19",
   "shorts": [{"id": "short05_frame_rate", "spec": "specs/short05_frame_rate.json",
               "slot": "12:30", "title": "...", "description": "...", "tags": ["..."]}]}

Spec timing: put the voice text in "voice": {"lines": [{"text": "..."}]}. A scene without "dur"
lasts as long as the next "lines" voice lines (default 1). The last scene gets a 0.6 s tail.
"""
import datetime, hashlib, json, os, re, subprocess, sys, urllib.request
from zoneinfo import ZoneInfo

FPS = 30
TAIL = 0.6
VOICE_ID = "TX3LPaxmHKxFdv7VOQHJ"  # Liam
MUSIC = ("https://ai-music-tracks.s3.us-east-1.amazonaws.com/9018c63d-2ffe-4e61-b2d2-c9b7fe996689/"
         "3d1eea42-ac70-465d-91ad-30f8f02f5b5f.wav")
RAW = "https://raw.githubusercontent.com/jfab3820/gta-stuff-guy/main/"
ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, ".cache")
WORK = os.path.join(ROOT, "work")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path + ".part")
        os.replace(path + ".part", path)
    return path


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout
    return float(out.strip())


def load(batch_path):
    batch = json.load(open(batch_path))
    for s in batch["shorts"]:
        s["_spec"] = json.load(open(os.path.join(ROOT, s["spec"])))
    return batch


def all_lines(batch):
    return [ln["text"] for s in batch["shorts"] for ln in s["_spec"]["voice"]["lines"]]


def voice_urls(voice_path):
    v = json.load(open(voice_path))
    v = v.get("result", v) if isinstance(v, dict) else v
    lines = v["lines"] if isinstance(v, dict) else v
    return [ln["audioUrl"] for ln in lines]


def time_spec(spec, durs):
    """Fill voice line start/dur and scene durations from the measured line lengths."""
    lines = spec["voice"]["lines"]
    t = 0.0
    for ln, d in zip(lines, durs):
        ln["start"], ln["dur"] = round(t, 6), round(d, 6)
        t += d
    ends = [ln["start"] + ln["dur"] for ln in lines]
    i, prev_f = 0, 0
    for n, sc in enumerate(spec["scenes"]):
        last = n == len(spec["scenes"]) - 1
        if "dur" in sc:
            f = prev_f + int(round(sc["dur"] * FPS))
            i += sc.get("lines", 0)
        else:
            i += sc.get("lines", 1)
            end = ends[min(i, len(ends)) - 1] + (TAIL if last else 0)
            f = int(round(end * FPS))
        sc["dur"] = round((f - prev_f) / FPS, 6)
        prev_f = f
    total = prev_f / FPS
    if total < t:
        raise SystemExit("%s: scenes (%.2f s) end before the voice (%.2f s)" % (spec.get("title"), total, t))
    return total


def publish_at(date, slot):
    h, m = map(int, slot.split(":"))
    y, mo, d = map(int, date.split("-"))
    return datetime.datetime(y, mo, d, h, m, tzinfo=ZoneInfo("America/Chicago")).isoformat()


def mix(base, voice_wav, music, total, out):
    fade = max(0.0, total - 0.8)
    fc = ("[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:{T},asplit=2[vo][sc];"
          "[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.5,atrim=0:{T},"
          "afade=t=out:st={F}:d=0.8[mu];"
          "[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[mud];"
          "[vo][mud]amix=inputs=2:duration=first:normalize=0,"
          "loudnorm=I=-15:TP=-2:LRA=11,aresample=48000,alimiter=limit=0.79:level=false[a]").format(T=total, F=fade)
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-i", voice_wav, "-stream_loop", "-1", "-i", music,
         "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow",
         "-tune", "animation", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-t", "%.3f" % total, "-movflags", "+faststart", out])


def check(path, spec):
    errs = run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"]).stderr.strip()
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    dur = duration(path)
    problems = []
    if errs:
        problems.append("decode errors: " + errs[:200])
    if not -16.5 <= lufs <= -13.5:
        problems.append("loudness %.1f LUFS" % lufs)
    if peak > -0.5:
        problems.append("peak %.1f dBFS" % peak)
    if dur > 59.0:
        problems.append("too long for a Short: %.1f s" % dur)
    # contact sheet: one frame per scene, at its midpoint
    t, picks = 0.0, []
    for sc in spec["scenes"]:
        picks.append(int((t + sc["dur"] / 2) * FPS))
        t += sc["dur"]
    sel = "+".join("eq(n,%d)" % p for p in picks)
    sheet = os.path.join(WORK, os.path.basename(path).replace(".mp4", "_sheet.png"))
    run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf",
         "select='%s',scale=270:-1,tile=%dx1" % (sel, len(picks)), "-frames:v", "1", "-vsync", "vfr", sheet])
    return {"duration": round(dur, 2), "lufs": lufs, "peak": peak, "problems": problems, "sheet": sheet}


def build(batch_path, voice_path, stills):
    batch = load(batch_path)
    urls = voice_urls(voice_path)
    texts = all_lines(batch)
    if len(urls) != len(texts):
        raise SystemExit("voice has %d lines, batch has %d" % (len(urls), len(texts)))
    music = fetch(MUSIC, "channel_music.wav")
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    report, k = [], 0
    for s in batch["shorts"]:
        sid, spec = s["id"], s["_spec"]
        n = len(spec["voice"]["lines"])
        parts = [fetch(u, hashlib.sha1(u.encode()).hexdigest()[:16] + ".mp3") for u in urls[k:k + n]]
        k += n
        durs = [duration(p) for p in parts]
        total = time_spec(spec, durs)
        timed = os.path.join(WORK, sid + ".timed.json")
        json.dump(spec, open(timed, "w"), indent=1)
        if stills:
            d = os.path.join(WORK, sid + "_stills")
            run([sys.executable, os.path.join(ROOT, "render_short.py"), timed, os.path.join(WORK, "x.mp4"),
                 "--stills", d], cwd=ROOT)
            print("%s: stills in %s (%.1f s)" % (sid, d, total))
            continue
        voice_wav = os.path.join(WORK, sid + "_voice.wav")
        inputs = sum([["-i", p] for p in parts], [])
        cat = "".join("[%d:a]" % i for i in range(n)) + "concat=n=%d:v=0:a=1[a]" % n
        run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", cat, "-map", "[a]",
             "-ar", "48000", "-ac", "2", voice_wav])
        base = os.path.join(WORK, sid + "_base.mp4")
        run([sys.executable, os.path.join(ROOT, "render_short.py"), timed, base], cwd=ROOT)
        out = os.path.join(ROOT, "out", sid + ".mp4")
        mix(base, voice_wav, music, total, out)
        qc = check(out, spec)
        sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
        item = {"id": sid, "file": "out/%s.mp4" % sid, "raw_url": RAW + "out/%s.mp4" % sid, "sha256": sha,
                "bytes": os.path.getsize(out), "title": s["title"], "description": s["description"],
                "tags": s.get("tags", []), "publishAt": publish_at(batch["date"], s["slot"])}
        item.update(qc)
        report.append(item)
        print("%s: %.1f s, %.1f LUFS, peak %.1f, %s" % (sid, qc["duration"], qc["lufs"], qc["peak"],
                                                      "; ".join(qc["problems"]) or "checks pass"))
    if not stills:
        rp = os.path.splitext(batch_path)[0] + ".report.json"
        json.dump(report, open(rp, "w"), indent=1)
        print("report:", rp)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, batch_path = sys.argv[1], sys.argv[2]
    if cmd == "lines":
        lines = all_lines(load(batch_path))
        chars = sum(len(x) for x in lines)
        print(json.dumps(lines, indent=1))
        print("# %d lines, %d characters, about %d credits (voiceId %s)" %
              (len(lines), chars, 28 * -(-chars // 1000), VOICE_ID), file=sys.stderr)
    elif cmd == "build":
        build(batch_path, sys.argv[3], "--stills" in sys.argv)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
