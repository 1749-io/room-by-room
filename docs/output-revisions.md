# Saving house work and recovering it

Run `python house.py status "Maple Cottage"` when you resume. The dashboard and room checks tell you what is reviewed or held. `python house.py history "Maple Cottage"` tells you who saved each change, what prompted it, which work it affects and the next action. A saved study can still show a failed design. The room and issue reviews determine what may be used or issued.

## Make or revise an output

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

Each revision save writes a separate ZIP under `House Renovation Backups/<house-id>/` in your user home folder. `history "House" REVISION` lists the archive name for saves made with automatic backup. To use a private external drive or protected synchronised folder, set `HOUSE_BACKUP_DIR` to its absolute path before saving. The default copy is on this computer. Keep the destination outside the checkout and house library. The ZIP contains the private material in clear text.

Pass the archive path printed by the save to `restore`. To take an additional backup between revisions, choose a fresh filename and use `backup` as in this example.

```sh
python house.py backup "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip"
python house.py restore "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip"
python house.py verify-revision "Maple Cottage" KITCHEN-R3
```

The backup includes the whole named house, including original sources, models, views, issued packs, working drafts, registers and revision records. It checks the published revisions and rereads the archive before publishing it. Restore validates the house identity and checksums in a temporary directory before installing files. In a fresh checkout it fills the missing private files. Identical files are retained. A second restore reports zero files if everything is present.

If the working house contains a conflicting file, recover into a separate directory to compare the two versions. For example, run `python house.py restore "Maple Cottage" "../private-backups/maple-after-kitchen-r3.zip" --to "../recovery/maple-cottage"`. Open the restored native files in their owning applications before resuming design. The [pier recovery exercise](../examples/whole-house-changes/README.md#recover-the-pier-revisions) shows this with a fictional house.
