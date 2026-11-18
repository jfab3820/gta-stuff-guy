# Atlas's daily Short

Set by Johnathan on Nov 18, 2026: Atlas (ChatGPT) makes one GTA Stuff Guy Short a day, a completely different kind of video from Cade's. Cade leads the channel. Cade checks Atlas's Short each morning and puts it in Johnathan's one daily approval with the others. Atlas contributes the video only: no uploads, no publishing.

## The format: "GTA 6 Today"

- A 20 to 40 second news recap in motion graphics: what happened with GTA 6 in the last 24 hours. That means official announcements, patches, events, records and Rockstar Newswire posts. On a slow day, do a "by the numbers" or a comparison card instead.
- Make it in HeyGen HyperFrames, through the HyperFrames connector in ChatGPT. Use kinetic text, icons, counters and simple maps, all drawn originally. That keeps it visibly different from Cade's host and list Shorts.
- Vertical 1080x1920, 30 fps, MP4.
- No voice by default. On-screen text carries it, which saves the shared vidIQ credits. For music, use the channel track (https://ai-music-tracks.s3.us-east-1.amazonaws.com/9018c63d-2ffe-4e61-b2d2-c9b7fe996689/3d1eea42-ac70-465d-91ad-30f8f02f5b5f.wav), HyperFrames' own licensed audio, or none. If there's no audio, Cade adds the channel track.
- First frame: the hook, fully on screen. Last card: a question and "Follow for more GTA 6".

## Rules

- **Original visuals only.** No Rockstar logos, key art, screenshots, trailer frames, gameplay footage or characters. No lookalike of a real person or a game character. No leaked or pre-release material.
- **Facts:** check every claim the same day you make the video, against two sources, one official where possible. List them in the delivery file.
- **No duplicates:** skip topics that `topics.md` marks ready or posted, and anything in `LOG.md`.
- **No spending:** if HeyGen asks for payment, or its free use runs out, stop and tell Johnathan. Do not upload to YouTube or create vidIQ social posts. Cade does that after review, and Johnathan approves.

## Delivery: by 10 PM Central the night before release

1. Import the final MP4 into vidIQ with `vidiq_video_upload`, attaching the file, and note the `uploadId`.
2. Commit one text file to your branch `atlas/mission-control-v3-foundation` in `jfab3820/levelup-command-center`, at `ai-ops/gta-stuff/atlas-daily/YYYY-MM-DD.json`. The date in the name is the release date.

```json
{
  "release_date": "2026-11-20",
  "topic": "Launch day by the numbers",
  "title": "GTA 6 ... (under 60 characters)",
  "description": "Two lines, ending with #gta6 #gtavi #shorts",
  "tags": ["GTA 6", "GTA VI", "..."],
  "vidiq_upload_id": "uuid from vidiq_video_upload",
  "duration_s": 30,
  "made_with": "HeyGen HyperFrames",
  "voice": "none",
  "music": "channel track | HyperFrames audio | none",
  "sources": [{"claim": "...", "urls": ["...", "..."], "checked": "2026-11-19"}]
}
```

A missed deadline means no Atlas Short that day, and there's no catch-up.

## Slot and review

- **Release slot, Central time:** 4:30 PM through Sun Nov 22, then 9:30 PM from Mon Nov 23. Cade's Shorts take the other slots.
- **Cade's morning check:** the file decodes cleanly, the length is right, and the loudness is set to -15 LUFS. A frame-by-frame look finds no logos, characters or footage and no text errors, and the facts are re-checked the same day.
- **If it fails:** the Short is held. The reason goes in `atlas-feedback.md` in this repo, so read that before making the next one.
- **First delivery:** Fri Nov 20, so by 10 PM Thu Nov 19.
