# GTA Stuff Guy

Pipeline for the GTA Stuff Guy YouTube Shorts channel (@gtastuffguy).

Start with the playbook: https://claude.ai/artifact/8tTd6yLDE365w9DZwzWj4M
The steps live in the `gta6-shorts-pipeline` skill. This repo holds the code and the art.

## What is here

| Path | What it is |
| --- | --- |
| `batch.py` | The daily run: one voice request for every Short of the day, local mix with the channel music, loudness at -15 LUFS, checks and a report. See `DAILY.md`. |
| `DAILY.md` | What the scheduled morning session does, step by step. |
| `topics.md` | Topic queue with sources. `LOG.md` lists what has been posted. |
| `render_short.py` | Renderer, v2. Text scenes over a still or moving background. 1080x1920, 30 fps, no audio. |
| `host.py` | Host layer for the renderer, v3. A talking puppet built from the four stills, and keyed green-screen motion clips. |
| `render_short_v1.py` | The v1 renderer, kept for reference. `patch_v2.py` turns it into v2. |
| `make_music.py` | Original synth bed and scene-cut effects. Add `sfx` as the 4th argument for effects only. |
| `specs/` | One JSON spec per Short. Copy the latest one as the pattern. |
| `assets/host/` | The original host character: four stills (mouth closed, half open, open; eyes closed) and `host_motion_hf01.mp4`, a Higgsfield motion clip on green. |
| `assets/backgrounds/` | Background stills and clips made in Gemini. Empty until Johnathan adds them. |
| `out/` | Finished videos that are too big for the 3 MB Drive upload cap. |

## Make the day's Shorts

Follow `DAILY.md`. In short: write the specs and `batches/DATE.json`, run `python3 batch.py lines`, voice them in one `vidiq_voiceover_generate` call, then `python3 batch.py build`.

## Make one Short by hand (older way)

```bash
python3 render_short.py specs/short02_file_size.json out/base.mp4 --stills stills   # look at these first
python3 render_short.py specs/short02_file_size.json out/base.mp4
python3 make_music.py sfx.wav 21.2 3.8667,8.4,12.9667,16.3667 sfx
ffmpeg -i out/base.mp4 -i sfx.wav -c:v libx264 -preset slow -tune animation -crf 25 -c:a aac -b:a 128k -shortest -movflags +faststart out/short.mp4
```

Needs Python with Pillow, numpy and scipy, ffmpeg, and the Poppins Bold and Medium fonts.

## The host (v3)

Add `"host"` and `"voice"` to a spec to put the host in a Short. `specs/short03_launch_stream.json` is the pattern.

- `"voice": {"lines": [...]}` takes each voice line's start, duration and text from `vidiq_voiceover_generate`. The puppet's mouth follows them. This is timed flapping, not true lip sync.
- Each scene shows the talking puppet by default. Set `"host": "none"` to hide him, or `"host": {"clip": "assets/host/host_motion_hf01.mp4", "from": 1.4}` to play a motion clip.
- With the puppet at the bottom, text gets `"safe": [200, 1000]`. A scene can set its own `"safe"`.
- Motion clip beats in `host_motion_hf01.mp4`: lean-in glare 0.3-2.7 s, point at camera 3.2-4.6 s, hands up 5.8-6.6 s, grin and nod 7-10.7 s. His mouth stays closed in the clip.
Through Short 4, voice and channel music were added in vidIQ. `batch.py` now mixes them locally, which saves the compose credits.

## Rules

The host is an original character. No lookalikes of game characters or real people.
No leaked footage, no isolated cutscenes, no re-uploaded clips without our own commentary.
Johnathan approves every upload.
