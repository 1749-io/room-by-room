# The Ryecroft Road film

[Watch the film (2 min 42 sec)](https://youtu.be/-4anR28Lqd8). A couple find a house that needs a lot of work, open Room by Room in a coding agent and watch it run every tool behind a renovation concept, from the CAD model to a dining room pack.

This folder is the film's source: the page that draws every frame, the data for each card, the pictures the cards show, and the scripts that time, score, render and master it. Ryecroft is a fictional house. Every figure on screen came from a real run of the named tool on that example, and [RUN-FIGURES.md](RUN-FIGURES.md) maps each one to the saved result it came from.

To make or re-cut a film like this, use the [Room by Room film skill](../../skills/room-by-room-film/SKILL.md).

## What is here

| Path | What it is |
| --- | --- |
| [film/channel.json](film/channel.json) | The film's content: brand, people, opening chat, 17 chapters and 29 cards, the pull-back map and the end card |
| `film/film.html` | The page that lays the cards out on one canvas and moves the camera. It draws any frame on request, so a render is repeatable |
| `film/assets/` | 23 stills, 13 frames of the live FreeCAD rebuild and the 168 frames of the eye-level walk that the film shows, all saved outputs of the example run |
| [film/scripts/](film/scripts/compose.py) | Timing, stills, checks and rendering (Node and Playwright), the music and sound (Python), and mastering (ffmpeg) |
| [publish/youtube.md](publish/youtube.md) | The title, description, chapters and tags used on YouTube, with the thumbnail |
| [RUN-FIGURES.md](RUN-FIGURES.md) | Where every figure comes from, what was drawn for the film, and which tools ran |

The rendered MP4, the WAV files and the rendered frames are not stored here. The scripts rebuild them.

## Rebuild it

Use Node 20 or later, Python 3.11 or later with NumPy and SciPy, and ffmpeg. The page uses Georgia, Segoe UI and Consolas from the rendering machine, so a render on another system substitutes its own fonts. Run these from `film/`.

```sh
npm ci
npx playwright install chromium
node scripts/timing.mjs             # channel.js and timing.json: 157.90 s, plus a 4.5 s closing card
python scripts/compose.py           # music/theme.wav, written to the film's bar grid
python scripts/mix.py               # assets/mix.wav: the music and 329 sound cues
python scripts/closing.py           # the final chord once more under the closing card
node scripts/qa.mjs                 # repeatable frames, pace and text that overflows its box
node scripts/stills.mjs 1.5         # stills/ with contact sheets. Review these before rendering
node scripts/render.mjs frames/full 10
bash scripts/master.sh frames/full renders/room-by-room-v8.mp4
```

`master.sh` sets the sound to -14 LUFS with a true peak at or below -1 dBTP and refuses to overwrite a file. Give each cut a new version number.

A rebuild from this folder on the machine that made the film gives the same `timing.json` and the same `assets/mix.wav`, byte for byte. Frames match except for sub-pixel differences in moving text.

## What you cannot rebuild from here

The pictures in `film/assets/` were cropped from the example house's saved revisions by [prepare_assets.py](film/scripts/prepare_assets.py). That house record holds native models, working files and revision archives, and it stays in private storage like any other house. The pictures are committed here so the film rebuilds without it.

To change a figure or a picture, rerun the tool on a fictional house, save the revision, update [RUN-FIGURES.md](RUN-FIGURES.md) and then the card.

## Credits and licences

- **Film rig.** The page and the Node scripts started from the channel-thread starter in [make-film](https://github.com/clsandoval/make-film) by Carlos Sandoval, under the MIT licence reproduced in [THIRD-PARTY.md](../../THIRD-PARTY.md#ryecroft-film).
- **Sound.** Synthesised by `compose.py`, `mix.py` and `closing.py`. Nothing is sampled, licensed or downloaded.
- **Pictures.** Saved outputs of the example run. The three room photographs and the armchair's product picture are AI concepts made from the model's own cameras and checked against them.
- **The armchair listing.** Invented for the example. The shop, the chair, the price and the link do not exist, and the link uses the reserved `.example` domain.
- **Site data.** Environment Agency LiDAR, containing public sector information licensed under the Open Government Licence v3.0. Building outlines and the road © OpenStreetMap contributors, Open Database Licence. Weather: climate.onebuilding.org TMYx, London Biggin Hill.
- **Names.** FreeCAD, Blender, QGIS, EnergyPlus, Codex and the other product names belong to their owners. No logos are used.

Nothing in the film is a survey, a structural design or a compliance check. The beam is a trial case for a structural engineer, and the programme and budget are the agent's allowances.
