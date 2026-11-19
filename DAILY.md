# Daily Shorts run

A scheduled session runs this every morning. It makes the day's Shorts, drafts them in vidIQ and waits for one yes from Johnathan. Johnathan set this up on Nov 18, 2026: one yes a day, 2 Shorts a day through Sun Nov 22, 3 a day from Mon Nov 23.

The rules in `CLAUDE.md` still hold: original host only, no leaked footage or isolated cutscenes, every fact checked the same day against two sources, and nothing publishes until Johnathan says yes in the Claude app to drafts he has seen.

## 0. Set up (about a minute)

- If this repo is not on disk, call `add_repo` for `jfab3820/gta-stuff-guy` with push access, run the clone command it returns, then `register_repo_root`.
- Check `python3 -c "import numpy, scipy, PIL"`, `ffmpeg -version` and that `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf` exists. The environment's setup script installs them; if one is missing, run `pip install numpy scipy pillow` or fetch the font from `https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/`.
- `vidiq_balance`. If it is under 150 credits, make one Short and say why.
- If the vidIQ tools are missing from this session, still pick and fact-check the topics and write the specs, then stop. Tell Johnathan the scheduled task needs the vidIQ connector added in the claude.ai routines settings, and do not try another way to upload.

## 1. Pick topics

- Count: 2 through Sun Nov 22, 3 from Mon Nov 23.
- Take the top `ready` or `verify` rows from `topics.md`. Skip anything posted already (see `LOG.md`).
- Check every claim today with WebSearch: two independent sources, one official where possible (Rockstar Newswire, PlayStation Blog, Xbox Wire, YouTube Blog). The container cannot open most pages, so read them through search results. If a claim does not hold up, cut it or pick another topic.
- Write the sources into the topic's row in `topics.md`.

## 1b. Atlas's Short (one a day, see `ATLAS.md`)

- `git -C /home/user/levelup-command-center fetch -q origin atlas/mission-control-v3-foundation`, then `git -C /home/user/levelup-command-center show origin/atlas/mission-control-v3-foundation:ai-ops/gta-stuff/atlas-daily/DATE.json`. If there is no file, there's no Atlas Short today. Say so in one line and carry on.
- `vidiq_video_upload` with its `vidiq_upload_id` gives a fresh `videoUrl`. Download it to `work/atlas_DATE.mp4` (storage.googleapis.com is reachable).
- Re-check its claims with WebSearch today, two sources each.
- Add it to the batch file as `{"id": "atlasNN_slug", "external": "work/atlas_DATE.mp4", "by": "Atlas", "slot": ..., "title", "description", "tags"}`, taken from his file. `batch.py build` fixes its loudness (adding the channel music if it is silent) and checks it.
- Look at its contact sheet for logos, game characters, footage or text errors. If it fails, leave it out of the batch, write the reason with the date in `atlas-feedback.md`, and tell Johnathan.
- Atlas's slot is 4:30 PM through Sun Nov 22, then 9:30 PM.

## 2. Write the specs

- One spec per Short in `specs/`, named `shortNN_slug.json`. Copy the nearest existing spec as the pattern.
- Put the voice text in `"voice": {"lines": [{"text": ...}]}`, one line per scene, and leave out scene `"dur"`: `batch.py` times scenes to the voice. A scene can take `"lines": 2`.
- About 20 to 30 seconds, 4 to 6 lines, under 330 characters of voice per Short, so a batch of 3 stays under 1,000 characters (28 credits).
- Line 1 is the hook and scene 1 is `"instant": true`. The last line asks a question and says follow.
- **Vary the look** across the day so the channel does not read as mass-produced (YouTube's inauthentic content policy):
  - **A, host talk:** `"host"` on, puppet at the bottom (`short03_launch_stream.json`).
  - **B, hook clip:** scene 1 plays `host_motion_hf01.mp4`, then cards with the host hidden (`"host": "none"`).
  - **C, no host:** big list rows or a countdown, `"bg": "drive"`, no `"host"`.
  - No two Shorts in a row share a look.
  - **Test, Nov 20 to 22:** both of Cade's Shorts use look C (no host, bold cards), because Studio on Nov 19 showed the HeyGen-style Short 4 at 1.1K views against 55 to 57 for the host-talk Shorts 3 and 5. The Sunday review decides whether the host stays.
- Write `batches/YYYY-MM-DD.json`: date, and for each Short its id, spec, slot, title (under 60 characters, starts with "GTA 6"), description (2 lines ending `#gta6 #gtavi #shorts`) and 8 to 12 tags.
- Slots, Central time: 12:30 and 7:30 PM for 2 a day; 12:30, 4:30 and 7:30 PM for 3 a day.

## 3. Make them

```bash
python3 batch.py lines batches/DATE.json        # prints the voice lines
```
Call `vidiq_voiceover_generate` once with `scriptLines` = that list and voiceId `TX3LPaxmHKxFdv7VOQHJ` (Liam). Save the whole result as `batches/DATE.voice.json`.
```bash
python3 batch.py build batches/DATE.json batches/DATE.voice.json --stills   # look at the stills
python3 batch.py build batches/DATE.json batches/DATE.voice.json            # final videos + report
```
- Look at every still, then every contact sheet (`work/<id>_sheet.png`). Fix any text that overflows, overlaps the host or misspells, then rebuild. `batches/DATE.report.json` must show no problems.
- Commit the specs, batch files and `out/*.mp4`, then push to main.

## 4. Draft

For each Short:
- `vidiq_video_upload` with its `raw_url` from the report.
- `vidiq_social_post_draft_create`: YouTube, platformAccountId `UCcGy6FUTnkkP3CxdwHZsfEA`, title, description as `text`, tags, categoryId 20, privacyStatus `public`, publishAt from the report.

Then end the turn with one message to Johnathan:
- Did / Next / You.
- Each Short: title, slot, length, and the file (send the mp4s with SendUserFile).
- Anything cut or uncertain from the fact check.
- The reply he can paste, in a copy box: `Yes, post all` (or `Yes except 2`).

## 5. When he says yes

- If a slot is less than 20 minutes away or past, move it to the next open slot today with `vidiq_social_post_draft_update`.
- Publish each approved draft with its latest revision, then check `vidiq_social_post_status`.
- Add a row per Short to `LOG.md`, mark the topics `posted` in `topics.md`, commit and push.
- Final message: Did / Next / You, with the YouTube links.

If he says hold or changes something, do that and nothing more. No reply means nothing posts.
