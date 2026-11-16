# GTA Stuff Guy

Pipeline for the GTA Stuff Guy YouTube Shorts channel (@gtastuffguy).

Start with the playbook: https://claude.ai/artifact/8tTd6yLDE365w9DZwzWj4M
The steps live in the `gta6-shorts-pipeline` skill. This repo holds the code and the art.

## What is here

| Path | What it is |
| --- | --- |
| `render_short.py` | Renderer, v2. Text scenes over a still or moving background. 1080x1920, 30 fps, no audio. |
| `render_short_v1.py` | The v1 renderer, kept for reference. `patch_v2.py` turns it into v2. |
| `make_music.py` | Original synth bed and scene-cut effects. Add `sfx` as the 4th argument for effects only. |
| `specs/` | One JSON spec per Short. Copy the latest one as the pattern. |
| `assets/host/` | The original host character: mouth closed, half open, open, eyes closed. Empty until Johnathan adds them. |
| `assets/backgrounds/` | Background stills and clips made in Gemini. Empty until Johnathan adds them. |
| `out/` | Finished videos that are too big for the 3 MB Drive upload cap. |

## Make a Short

```bash
python3 render_short.py specs/short02_file_size.json out/base.mp4 --stills stills   # look at these first
python3 render_short.py specs/short02_file_size.json out/base.mp4
python3 make_music.py sfx.wav 21.2 3.8667,8.4,12.9667,16.3667 sfx
ffmpeg -i out/base.mp4 -i sfx.wav -c:v libx264 -preset slow -tune animation -crf 25 -c:a aac -b:a 128k -shortest -movflags +faststart out/short.mp4
```

Needs Python with Pillow, numpy and scipy, ffmpeg, and the Poppins Bold and Medium fonts.
Voice and channel music are added in vidIQ. The playbook has the voice id, the music link and the upload steps.

## Rules

The host is an original character. No lookalikes of game characters or real people.
No leaked footage, no isolated cutscenes, no re-uploaded clips without our own commentary.
Johnathan approves every upload.
