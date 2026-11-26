# Opening and installed clearances

At proposed CAD, inventory each place where an opening or moving fitting can meet nearby construction, joinery or another fitting. Use the room sources and inspect a section at hardware height. Include the installed body, leaf, handles and projecting trim, worktops, reveals, sills or valves where their heights and operating areas coincide. Test neighbouring moving parts together when the routine needs both. Include the whole movement from shut to the angle or extension needed to use, unload or service it. Two clear end positions can conceal a clash part-way through.

Reopen the native model. Export the installed parts, complete swept envelopes and affected projections as polygons in plan with bottom and top levels, in a common frame in millimetres. Use multiple solid envelopes to represent stepped or discontinuous features. A conservative enclosing envelope can establish separation. Confirm a suspected intersection with the native solids or mesh at a witness position. Bound angular sampling error or use a continuous native sweep. State the required working clearance and dimensional uncertainty from this job. A missing measurement that can reverse the finding keeps it on hold.

Place the report in the revision outputs at `openings/<room-id>.json`. This short example describes a sliding drawer beside a shelf. Replace the illustrative dimensions and digest with the reopened model read-back. Model paths start at the revision directory.

```json
{
  "revision": "R3",
  "room": "study",
  "units": "mm",
  "model": "outputs/Study.FCStd",
  "model_sha256": "<SHA-256 of the native file>",
  "basis": "Joiner's measured section and the selected runner travel.",
  "geometry": {
    "case": {"xy": [[0,0],[400,0],[400,500],[0,500]], "z": [0,800]},
    "drawer and pull": {"xy": [[0,480],[400,480],[400,950],[0,950]], "z": [580,700]},
    "shelf lip": {"xy": [[100,650],[450,650],[450,690],[100,690]], "z": [715,750]}
  },
  "zones": [{
    "name": "Drawer beside the shelf",
    "travel": "Shut to 450 mm extension, including the projecting pull",
    "installed": ["case"],
    "sweeps": ["drawer and pull"],
    "obstacles": ["shelf lip"],
    "required_mm": 8,
    "uncertainty_mm": 3
  }]
}
```

Run `python house.py check-openings "House" "Room" --input-revision R3` in the open or saved revision. Every listed part is tested against every listed obstacle at its actual height. Contact, insufficient margin, an unknown tolerance (`null`), stale native evidence or a missing shape holds the affected proposal. If there genuinely is no operating interface, retain the source and write an empty zones list with a room-specific `no_interfaces_reason` after inspection.

Before showing an operating concept or releasing a furnished camera, repeat the inventory from the actual reopened Blender scene at `openings/<room-id>.camera.json`. Use its model path, digest, envelopes and `cad_revision`. Match the stable IDs for equivalent interfaces in both apps. If dressing introduces a projection or changes an envelope, take it back to CAD. Run `check-openings` with `--camera`. Add `--cad-revision R3` if the camera lives in a later draft. The command checks the declared inventory and measured envelopes. The reviewer identifies visible features and ensures those dimensions and envelopes represent the objects and the whole movement.

`check-layout` enforces the CAD clearance report. `check-render ... blender --input-revision R3` also checks the furnished report before rendering. Supply `--scene-revision R4` when the prepared scene lives in a separate snapshot or open draft. Existing project records can explicitly identify a previously accepted legacy revision. Recheck the affected revision when the assembly, hinge, handle, fixed projection or native scene changes. A saved diagnostic for a failed design should show the clash, name the measured return or redesign needed, and retain the hold.

## Check the doorway in elevation

Inventory each architectural door seen from or operating in the room, including doors beyond it, before dressing or rendering a concept. Give the opening a stable ID. Inspect a face-on elevation and a cut through the wall thickness with the leaf shut. Check both jambs, lining, reveal, head, and what fills the field above the leaf. Then check the moving leaf, track or hinges and handle in the open state. Interior, exterior, sliding, folding and glazed doors follow the same stages.

In the existing opening evidence add a `door_heads` object keyed by opening ID. Use an empty object and a specific `no_doors_reason` for a genuinely door-free scope. Each door records:

- `basis`, `design_reference` and `design_sha256` identify the selected elevation or documented planning assumption frozen under the CAD revision's inputs or outputs.
- `field_mm: [width, height]` describes the clear section at the doorway, from the shut leaf top to the finished partition top. Include the operating reveal. For split or stepped assemblies, describe separate rectangular fields under distinct IDs.
- `expected` and `observed` each tile that field using pieces with `id`, `role` and `xz` polygon vertices in millimetres. Roles are `opaque`, `glazing` and `open`. Use the same origin and precision. Take the observed section from the reopened native geometry. Measure air intervals too. Section the actual wall plane so a ceiling, foreground leaf, projecting trim or nearby wall cannot fill a missing head by projection.
- Derive the expected section from the cited design. Model deliberate fanlights, open heads and reveals explicitly. If the design is unresolved, identify who will settle it or document a provisional treatment for planning. A photo reviewer cannot certify an engineer's lintel or bearings.

Run `house.py check-openings HOUSE ROOM --input-revision CAD` for the CAD handover. Run it again with `--camera --input-revision SCENE --cad-revision CAD` for the reopened furnished model. For expressly authorised concept pictures, add `--door-heads-only` to check these elevations even while unrelated fit decisions remain open. That narrower result applies only to the doorway section. Include the evidence with the visual's purpose approval. A changed assembly requires a fresh native read-back and inspection of all views looking into it.

Earlier opening reports without a door inventory need a new read-back for a current issue. Keep their saved receipts and images as issued.
## Applying a saved correction to a registered room

An opening report belongs to the native model identified by its SHA-256. A later head detail can supplement a room review without editing the original revision. The original room and the corrected study each need a saved CAD report and furnished-scene report.

1. Begin a new private revision. Use four `--input` arguments for the two reports at each revision, for example `revisions/R2/outputs/openings/study.json` and `revisions/R2/outputs/openings/study.camera.json`, then the equivalent pair from the corrected revision.
2. In its outputs, write `opening-addenda/study.json` with `room`, `source_revision`, `study_revision` and `reviewer`. Record the room slug, the original registered revision, the saved corrected study and who compared them. Save this revision with the usual reason, effects and next action.
3. In `rooms/study/opening-review-addendum.json`, set `source_revision` to the original revision and `revision` to the newly saved addendum revision. The room status and house handover now check the recorded correction. Use `house.py check-openings "House" "Study" --input-revision R2 --current` and repeat with `--camera`. Add `--door-heads-only` for an elevation-only result. Omitting `--current` inspects the named study on its own.

If the native bytes are identical, a verified head-only study can reuse the original operating measurements. A changed model requires fresh full-travel measurements of its installed bodies, moving parts and obstacles. Keep previous contacts and unresolved uncertainty on hold. A change intended to resolve an operating clash needs a new occupied room review. Record survey and supplier returns separately.
