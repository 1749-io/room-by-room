---
name: room-by-room-film
description: Make, re-cut or re-render a film or clip about Room by Room, such as a walkthrough of an example house, a feature film, a social cut or a new version of the Ryecroft Road film. Use whenever someone asks for a Room by Room video, film, clip, teaser or thumbnail, or wants to change a previous one. It layers the project's brand, truth rules, privacy rules and folder conventions on top of the make-film skill, which does the directing, gates and rendering.
---

# Room by Room film

This skill is a layer on **make-film** ([github.com/clsandoval/make-film](https://github.com/clsandoval/make-film), MIT). make-film owns the method: style routing, the seven gates, repeatable frames, the render rig and QA. This skill owns what is specific to Room by Room: what a film may show, where each figure comes from, the brand, the folders and the record of past cuts. Where they disagree, the director's instructions win, then this skill, then make-film.

The reference film is the [Ryecroft Road film](../../examples/ryecroft-film/README.md): its source, pictures and scripts are in the repository and rebuild as documented there.

## When to use

- A new film or clip about the toolkit, an example house or a single feature.
- Changing, re-cutting, re-rendering or re-titling a previous film, or remaking its thumbnail.
- Not for a first-person visit to a house: use the [Blender house walkthrough](../blender-house-walkthrough/SKILL.md). Not for a room photograph or a handover pack: use [Blender interiors](../blender-interiors/SKILL.md) and [pack delivery](../pack-delivery/SKILL.md).

## The film shows the toolkit at work

A Room by Room film follows one household and one house. Each question starts in a chat and opens into the artifact the tool produced, with the call that made it shown beneath. The viewer sees the tools working, in the order a real commission meets them.

- Structure the film as the household's questions, in order. Do not tour the toolkit's features.
- Every card earns its place by answering the question before it. Show a result when it changes a decision.
- Let the household decide on screen. A choice sheet, their answer and what changed next read better than a finished render alone.
- Show what the run did not settle: a room on hold, a width still to measure, a beam left for the engineer. The film is more convincing for it.
- Keep drawn interface and real output apart. A real render or photo fills its card. It never shares a frame with drawn chrome that could pass for it.

## Before you start

1. **Install make-film, update it and read it.** Clone it to your agent's skills folder if it is missing, pull the latest revision, then read its `SKILL.md`, the chosen style's `RECIPE.md` and its `references/` on direction, copy, truth, motion, sound, QA and deliverables. Record the revision used in the film's handoff. The Ryecroft film used the channel-thread style at revision `1dee171`.
2. **Read the reference film.** Open its [README](../../examples/ryecroft-film/README.md), [RUN-FIGURES.md](../../examples/ryecroft-film/RUN-FIGURES.md) and [channel.json](../../examples/ryecroft-film/film/channel.json), and watch the published film where you can.
3. **Choose the house.** Use a fictional example with a saved run behind it. Read [what a film may show](references/truth-and-privacy.md) before taking a single picture from it.
4. **Check the tools.** Node 20 or later, ffmpeg and ffprobe, Python with NumPy and SciPy, and Playwright's Chromium.
5. **Check the brand** against [brand.md](references/brand.md) and the repository's current README and logo.

## Truth and privacy in one screen

The full rules, with the reasons, are in [truth-and-privacy.md](references/truth-and-privacy.md).

1. **Every figure comes from a saved result of a real run** of the named tool. Keep a `RUN-FIGURES.md` table of what is on screen, the value and the file it came from. A figure without a row does not ship.
2. **A tool is named only if it ran.** List the tools that were planned and did not run, and leave them out of the film.
3. **Say what was drawn for the film:** chat lines, window chrome, a listing card, captions.
4. **Label an AI photograph as an AI concept**, make it from the model's own camera and review it against that camera.
5. **Never present a concept as a survey, a structural design or a compliance check.** A beam is a trial case for a structural engineer. Costs and durations are the agent's allowances.
6. **Use a fictional house. Take nothing from a property listing:** no photograph, traced plan, price, portal or agent name, and no house number.
7. **Keep household material out.** Nothing from a real commission under `houses/` appears in a film.
8. **Name products in words, without logos.** An invented shop or product uses the reserved `.example` domain and is recorded as invented.
9. **Synthesise the sound or clear it.** Record the source and licence of anything not made for the film.

## Authorisation

- Research, stills and local rendering need no further approval.
- Ask before any paid call, including an image tool, and keep a ledger of calls in the film folder.
- Ask before publishing or posting anywhere, including a pull request that adds film pictures to the public repository.
- Ask before downloading music, fonts or footage. Name the file, source, size and licence.

## Workflow

Follow make-film's gates in order. These notes are the Room by Room additions.

| Gate | Addition |
| --- | --- |
| Brief | State the house, the household's question, the destination and aspect, and which earlier cut this follows. |
| Script lock | Write the on-screen words as a table with every figure as a named slot. Fill the slots from the run, then read the script through once. If the run changes the story, change the script and say so. |
| Motion preview | Render 20 seconds from the busiest stretch. Judge pace in motion, never from stills. |
| Frame review | Someone other than the author reads the contact sheets for text that is cut off, colliding labels, empty frames and anything that contradicts `RUN-FIGURES.md`. |
| Full render | Version every file and never overwrite one. `master.sh` refuses to. |
| Review | Decode frames from the delivered MP4, count them, and measure the sound. Search the film's data for any name that must not appear. Say plainly when the sound was measured and not listened to. |
| Deliver | Log the file and its checks in `DELIVERY.log`. Write `HANDOFF.md` with the open questions for the director, what the film does not show and why, the credits and what you would fix next. |

After a change to a delivered cut, compare every frame of the new render with the previous one and confirm that the differences fall only where the change was made.

## Folders

Work in a film folder outside the repository. A full render writes several gigabytes of frames.

```text
<house>-film/
  BRIEF.md  HANDOFF.md  DELIVERY.log  RUN-FIGURES.md
  publish/            title, description, chapters, tags and the thumbnail
  film/
    channel.json      the film's content
    film.html         the page that draws every frame
    assets/           pictures cropped from the run's saved revisions
    scripts/          timing, stills, QA, render, music, mix and master
    stills/ frames/ renders/ music/     rebuilt outputs
```

When a film is published and the director asks for its source in the repository, copy the publishable part to `examples/<house>-film/` as the reference film does:

- Include the page, `channel.json`, the scripts, the pictures the cards use, the publish notes and `RUN-FIGURES.md`.
- Leave out rendered frames, MP4 and WAV files, working notes, superseded pictures and any script that still holds an earlier draft's words.
- Replace machine paths with arguments. Search every text file for names that must not be published.
- Open every picture before adding it. Record each one, and every file type the public-tree check does not treat as text, in the [asset inventory](../../examples/asset-inventory.json) with its origin and rights.
- Add licence notices to [THIRD-PARTY.md](../../THIRD-PARTY.md) and rebuild from the committed copy to confirm that the timing and the sound still match.

## Re-cut the reference film

Copy `examples/ryecroft-film/` to a working folder and follow its [rebuild steps](../../examples/ryecroft-film/README.md#rebuild-it). Edit `channel.json` for words, figures and card order. Edit `film.html` for layout and motion. Rerun `timing.mjs` after either, then the music and mix, since both follow the timing.

## Previous films

[films.md](references/films.md) records each cut of the Ryecroft film, what changed and what was learned.
