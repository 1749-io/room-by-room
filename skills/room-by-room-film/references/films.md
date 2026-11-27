# Previous films

A record of each cut, what changed and what was learned. It is history, not a rule: the rules are in [SKILL.md](../SKILL.md) and [truth-and-privacy.md](truth-and-privacy.md).

## The Ryecroft Road film

Source: [examples/ryecroft-film](../../../examples/ryecroft-film/README.md). Published: [youtu.be/-4anR28Lqd8](https://youtu.be/-4anR28Lqd8). Style: make-film channel-thread. House: Ryecroft, a fictional three-bedroom inter-war semi with the agent's own plan, placed on a real road for its public site data.

| Cut | Length | What changed |
| --- | --- | --- |
| 3 | 122.5 s | The first cut on the fictional house, in the format already approved: a chat, then one canvas of cards joined by a line. |
| 4 | not logged | Rendered and not sent. |
| 5 | 145.3 s | New music composed to the film's own timing. An armchair listing that goes onto the shopping list and into the model. A new conservatory chapter: sliding doors, a live FreeCAD build, the Blender camera and the photo. |
| 6 | 157.9 s | One final design through the whole film. New order: the all-year choice, the rebuild with its roof insulation, the room's temperature through the year, the armchairs and doors, then Blender and the walk. A modelled garden. |
| 7 | 162.4 s | The repository's new address on the clone card and end card, and a 4.5 second closing card with the final chord once more. Every other frame matches cut 6. |

## What was learned

- **One design all the way through.** Cut 5 changed the conservatory late, so the walk and the plan still showed the earlier doors and chairs. Cut 6 rebuilt the house as one revision and took every picture from it. Decide the final design before making pictures.
- **Keep an approved format.** When a form has been approved, a new cut changes content and leaves layout, pace and card design alone.
- **Pace is judged in motion.** 104 beats a minute read as slightly too fast between cards. 95 with slower moves was right. A wider layout with quicker moves in cut 5 was reversed in cut 6.
- **Compose to the timing.** From cut 5 the music is written from `timing.json`, so the drop, the quiet stretch under the eye-level walk and the final hit land where the film puts them, and the same timing gives the same file.
- **Give a view something to look at.** Glazing with nothing modelled beyond it shows a blank sky. A simple garden, with trees at their surveyed heights, gives the walk an ending and the image tool a garden to follow.
- **Follow the run.** When the real run changes the story a script was locked on, rewrite the beat to what happened.
- **Redraw a faulty sheet from the same results.** A label outside its box or a key over the data is fixed by redrawing the sheet from the saved figures, and the saved revision is then re-issued.
- **Prove a small change is small.** Cut 7 compared all 4,737 earlier frames with the new render: 389 differed, all where the address changed. One frame differed by render noise at text edges and was replaced with the earlier frame.
- **Sub-pixel text noise is normal.** Two renders of the same moving label can differ by a fraction of a pixel. Compare content, not checksums, across machines and sessions.
- **Say what was not checked.** Each delivery records that the sound was measured and not listened to, and whether an independent frame review was run.

## Still to do on this film

1. A 9:16 cut. Only the 16:9 master exists.
2. Make the opening chat read as a phone, not a desktop window.
3. An independent frame review of the delivered cut.
