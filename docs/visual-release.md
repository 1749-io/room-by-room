# Design decisions and visual release

An accepted arrangement lives in the named house. Its drawings and photographs can be revised independently. Before publishing a visual, match the actual placement to the design state, the reviewed derivative and its source bytes. The [fictional replay](../examples/visual-release/README.md) writes populated registers and builds two brochures.

## Record the design before reviewing a picture

Keep `design-states.json` at the house root. The top level has `version: 1`, the house ID and a `states` object keyed by stable state IDs. A state records the phase, status, scopes, design revision, arrangement in household language, exclusions, geometry references, consequential features and superseded IDs.

- Use `observed` for existing fabric. Link the saved survey or geometric basis. Use `for-review` for a proposed option still awaiting a decision. A proposed comparison brochure or final photo issue requires `accepted`.
- Keep the editable native geometry or parametric source in its saved revision. Each geometry reference contains a house-relative `path`, `revision` and SHA-256. Include both the parameters and the generator when the geometry is procedural.
- For acceptance, retain the homeowner's actual dated words. Record the person, scope, exclusions and the precise arrangement and geometry they accepted. A `homeowner_decision` links the original instruction or `handover-answers` JSON and the separately saved acceptance binding. The binding records the house, state ID, decision hash, quotation, person, date and `arrangement_sha256` calculated by `house_visuals.arrangement_signature`. Create it only after reconciling the actual reply with the state. Keep construction, structural, purchasing and consent decisions in their own professional or purchase records.
- Name consequential features independently of the available images. For each, give a description, the affected room and floor scopes, and the view types that must show it. For example, a retained opening may require both a plan and a section. Use stable scopes such as `room/library` and `floor/ground`. Include both scopes when the room photograph and the floor drawing need the same feature.

Read the accepted design directly, including when there are no derivative images.

```sh
python house.py check-design "House" DESIGN-STATE --scope floor/ground
```

## Sign off a derivative for its use

Keep `visual-approvals.json` beside the design register, with the same version and house ID. Its `visuals` object is keyed by stable visual IDs. An approval records its state ID and state hash, `signed` status, representation such as `plan`, `section`, `photo` or `locator`, saved source path, revision, SHA-256 and source page where applicable. Record the reviewer, limitations, dependencies, feature findings, supersession and the approved purpose/scope pairs. State and visual supersession use lists of earlier IDs. Retain the earlier records.

The renderer supplies the placement purpose. A room component uses `drawing` or `room-review`. An exact component forwarded in the house pack retains its original purpose and page trace. Other placements need their own grant.

| Destination | Approved purpose |
| --- | --- |
| Homeowner presentation | `homeowner-presentation.opening` for the decision page, `homeowner-presentation.room` for room pages |
| Architect pack | `architect-pack.drawing` for the included sheet and its copy in the print set |
| Buyer brief | `buyer-brief.scenario` for the purchase scenario, `buyer-brief.room` for room pages |
| Comparison brochure | `comparison.cover`, `comparison.layouts`, `comparison.rooms`, `comparison.studies` or `comparison.particulars`, according to the page |
| House photo archive | `photo-pack.room`, `photo-pack.exterior` or `photo-pack.attachment` for additional visual files |

A brochure floor layout always requests a plan for its actual floor. A room page can use an explicitly approved locator.

For a camera or photo, link the independent framing record via `camera` and `framing`. It identifies the camera, native-camera or survey-photo basis, state hash, reference evidence and expected visibility for every consequential feature in the linked arrangement. Check adjoining spaces visible through an opening and features seen from the exterior. A visible feature requires a `shown` observation. An `outside-frame` or `obscured` finding needs the matching camera result, an explanation and hashed evidence. Use an annotated frame, sightline read-back or native camera comparison that shows why. The reviewer inspects the geometry and pixels and records that judgement. The release check verifies those records and the actual bytes at publication.

```sh
python house.py check-visual "House" APPROVED-PLAN --phase proposed --purpose comparison.layouts --scope floor/ground --view plan
```

## Correct and reissue

Return the failed placement to its source decision, native model or derivative review. A new layout decision gets a new state ID and records which state it supersedes. A corrected view gets a new visual ID with its own source bytes and review. Re-run the affected placements and check repeated uses in decks, room pages, sheets, the standalone brochures and the combined PDF. A replacement review can cite an existing accepted state when the arrangement is unchanged.

New component issues keep full placement evidence in the private issue manifest. The brochure builder records each use in `Visual-uses.json`, with the HTML anchor, slot and separate and combined PDF page numbers. It checks the displayed pixels on those pages. Revision save reopens the brochure and rechecks current approvals. Keep the two registers in place when beginning a revision so its private input snapshot captures the contemporaneous records. Existing standalone historical issues remain readable. Reissue an older source component with its placement approvals before assembling it into a new current pack.
