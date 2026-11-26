# Saving house work and recovering it

Run `python house.py status "Maple Cottage"` when you resume. The dashboard and room checks tell you what is reviewed or held. `python house.py history "Maple Cottage"` tells you who saved each change, what prompted it, which work it affects and the next action. A saved study can still show a failed design. The room and issue reviews determine what may be used or issued.

## Record the next homeowner choice

For a full furnished room, an internal checkpoint can be saved while the photo or pack is pending. A next-work invitation through `save-revision --ask` waits for the completed issue. Use `ask` for a real mid-study decision. At full handover the archive must contain each checked final image. [Furnished issue checks](../skills/renovation-pack/references/handover-gates.md#finishing-a-furnished-room)

For a spatial or visual choice, show the homeowner the checked image inline with the question. Include a one-sentence description so they can also answer from the text. Add `--ask-image "drawings/serving-options.png" --image-description "A serves from the kitchen side. B passes the chair beside the radiator."` to the save command after placing that labelled image in the revision's outputs. The saved question, `next`, `status` and the restored backup point back to that same image.

The agent [writes the question from the current brief and findings](../skills/renovation-pack/references/homeowner-decisions.md#at-the-end-of-a-commission). Pass the whole prompt to `--ask`, including any examples or invitation to move on, so it reads the same on resume. Use `--next` for the action and its owner. An internal save can use `--next` alone.

```sh
python house.py ask "Maple Cottage" KITCHEN-R3 --ask "Would you keep the side cupboard or compare a rear-wall hob to free both serving points?" --ask-image "drawings/serving-options.png" --image-description "A keeps the cupboard. B moves the hob and frees both pickups."
python house.py save-revision "Maple Cottage" KITCHEN-R3 --change "Compared two serving routes" --why "Serving crosses the cook" --by "Design reviewer" --affects "Kitchen and dining" --next "Choose which routine to design for"
python house.py next "Maple Cottage"
python house.py answer "Maple Cottage" KITCHEN-R3 "Compare the rear-wall hob and keep both serving points."
```

Use the homeowner's actual reply. A reply already present in the conversation can be recorded directly. Update the affected briefs and decisions, then continue the chosen work. `status` and `next` show the outstanding question or recorded reply. `next "Maple Cottage" KITCHEN-R3` looks up a particular handover. The reply lives beside the immutable revision in `handover-answers/` and is captured with the next revision's inputs and backup. A later change of mind belongs in a new dated decision.

During a study, `ask` records the question and checked image digest in the open draft. Present its Markdown image, description and question together in chat. `next` can replay it and `answer` can record a reply before publication. Saving carries the question forward and verifies the same image. You can also pass the fields directly to `save-revision`. An image must decode as a PNG, JPEG or WebP using Pillow (`python -m pip install Pillow`). New questions default to visual. Supply `--question-kind timing`, `budget`, `scope` or `administration` when the choice can genuinely be made from text. An ordinary revision without a question keeps its existing save behaviour.

## Make or revise an output

The draft captures the working checklist and survey register as inputs when present. A saved revision refreshes the live checklist. After restoring a backup, run `python house.py checklist "House"` to read the restored evidence against the current gates.

1. Choose a house-wide revision ID such as `KITCHEN-R3`. Start with `begin-revision`. Use `--from` with the specific saved revision you are changing. For a first snapshot of existing work, supply its house-relative file paths with repeated `--input` flags. Include the instruction, survey or drawing that governs the change.
2. The command prints a private working directory. Write the CAD Save As, rendered view, calculation, spreadsheet or issue there. It contains editable copies of the parent outputs. The sibling `inputs/` directory captures the working brief and decision log by default, plus the named sources as they stood at the start. Preserve relative paths for textures and other dependencies. Reopen and check the working output using the appropriate house skill. If you resume before saving, `status` lists the open draft and its files are under `.revision-work/<ID>/outputs/`.
3. Finish file writes and run `save-revision`. Record the change, its reason, the person or agent responsible, what else it affects and the next action. The command prepares the revision, includes it in a full private backup, rereads the archive to verify its contents, then publishes the revision and prints the backup path. If backup verification fails, the draft is available to retry with the same ID. Use a new ID for a correction to a published revision.
4. Link the saved output from the room review or house dashboard. For example, use `revisions/KITCHEN-R3/outputs/occupied-plan.pdf` in `review.csv`. Record the actual design revision in the review row. Name affected rooms, tenders, budgets and issued packs, and update their holds or decisions where appropriate. The latest saved study may be an alternative. Keep the currently issued pack linked until its replacement passes review.

The following example assumes the survey is already registered under the named house and `KITCHEN-R1` is its saved baseline.

```sh
python house.py begin-revision "Maple Cottage" KITCHEN-R3 --from KITCHEN-R1 --input "source/pier-survey.pdf"
# Save the revised plan and measured route in the printed outputs directory.
python house.py save-revision "Maple Cottage" KITCHEN-R3 --change "Shortened the end unit and moved dry prep" --why "The surveyed pier narrows the route for eight diners" --by "Design reviewer" --affects "Kitchen storage, dining route and both tenders" --next "Owner to confirm utility storage before tender"
python house.py history "Maple Cottage" KITCHEN-R3
python house.py verify-revision "Maple Cottage" KITCHEN-R3
```

The record at `revisions/<ID>/record.json` stays inside the private house library. It identifies the toolkit commit at save time and whether the checkout had local changes, when Git is available. Use shareable descriptions and filenames there. Sources, captured inputs, output files and working copies stay private. After saving, edits to the working copy leave the saved revision intact. Treat the published folder as read-only in desktop applications. Verification detects external changes. A room review that relies on changed snapshot evidence goes on hold.

New houses use saved output evidence for each design handover after the brief. Older version 1 houses can use the commands immediately and retain their previous reviews. For a version 2 upgrade, list any already-reviewed revision IDs by room in `legacy_output_revisions` in `project.json`. Keep subsequent work under new IDs.

## Back up or restore one house

To open a project on another computer, restore its private backup and verify the saved revision. The public checkout contains only the toolkit and worked examples.

Run the [fictional recovery exercise](../examples/whole-house-changes/README.md#recover-the-pier-revisions) to test a restore before relying on it.

Each revision save writes a separate ZIP under `House Renovation Backups/<house-id>/` in your user home folder. `history "House" REVISION` lists the archive name for saves made with automatic backup. To use a private external drive or protected synchronised folder, set `HOUSE_BACKUP_DIR` to its absolute path before saving. The default copy is on this computer. Keep the destination outside the checkout and house library. The ZIP contains the private material in clear text.

Pass the archive path printed by the save to `restore`. To take an additional backup between revisions, choose a fresh filename and use `backup` as in this example.

```sh
python house.py backup "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip"
python house.py restore "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip"
python house.py verify-revision "Maple Cottage" KITCHEN-R3
```

The backup includes the whole named house, including original sources, models, views, issued packs, working drafts, registers and revision records. It checks the published revisions and rereads the archive before publishing it. Restore validates the house identity and checksums in a temporary directory before installing files. In a fresh checkout it fills the missing private files. Identical files are retained. A second restore reports zero files if everything is present.

If the working house contains a conflicting file, recover into a separate directory to compare the two versions. For example, run `python house.py restore "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip" --to "../recovery/maple-cottage"`. Open the restored native files in their owning applications before resuming design. The [pier recovery exercise](../examples/whole-house-changes/README.md#recover-the-pier-revisions) shows this with a fictional house.

## Keeping automatic backups small

The first automatic save creates a full private ZIP. Later saves store one copy of each changed content hash beside the newest full ZIP for that house. Each revision can be restored with its own ZIP and the named full base. Copy those two files together. Manual backups remain standalone full ZIPs. Restore through the house command so every recovered file is verified.

Run `python tools/backup_retention.py DIRECTORY` against the private single-house directory for a read-only size report. Keep the newest recoveries, their full bases, and any milestone or unsaved work still needed. Before removing older snapshots, restore to a separate folder and check the required historic revisions. When deltas approach the size of a full backup, create a new standalone full backup in the same directory, verify it and start the next group there. Old deltas continue to require their original base.

## Issuing selected components

Use `begin-revision --pack-request` for a declared recipient issue. The saved request makes the file list and reader check mandatory on this revision. A new delivery starts with a clean output folder, including when a parent supplies the design basis. The saved envelope is `revisions/<issue>/outputs/pack/` and its ZIP contains the recipient tree. The regular revision commands still support design checkpoints and legacy issues. [Commands and examples](../skills/pack-delivery/SKILL.md)
