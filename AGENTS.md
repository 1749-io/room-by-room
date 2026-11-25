# Working on a house

On resuming, read `python house.py history "House"` alongside the dashboard and room reviews. Before producing or revising an output, use `begin-revision`, work in the printed private directory and `save-revision` with its inputs, change, reason, author, effects and next action. The save verifies a private whole-house backup before publication. Link the saved output at handover. Follow the [revision and recovery guide](docs/output-revisions.md).

Use the [worked examples](examples/README.md) to find a relevant replay or handover. Use the current house's brief, permissions and geometry for live decisions.

For a whole-house commission, start with the [shared decisions and dependencies](skills/renovation-pack/references/whole-house.md). For a UK alteration, use the [nation-specific consent enquiry](skills/renovation-pack/references/uk-consents.md) when it affects the decision.

Run [route studies](skills/freecad-renovation/references/route-studies.md) behind the existing CAD reviews. Use the household's routine, occupied geometry and change permissions. Report a current pinch during an assessment. During design, try only permitted alternatives and rerun linked journeys before release.

Review the colours together in every furnished room and record a current `room-palette` finding before final AI. Ask the homeowner about any consequential open choice, check each issued AI photo against its Blender camera and check the decorator schedule when issuing physical finishes. Follow the [renovation-pack colour workflow](skills/renovation-pack/references/colour-decisions.md).

For a new project, follow the root [intake and startup guide](README.md#start-a-project). Accept the homeowner's materials in their supplied form, fill the working brief from available evidence and ask only for gaps that affect the next decision. Use the [same review stages](README.md#design-and-review-stages) for every property.

Write in British English. Use the named house under `houses/` as the project root. Run `python house.py list` to locate one. For a new house, run `python house.py start`, supplying the original brief file if available. Do not apply one house's layouts, furniture, budget or design choices to another house.

Read the house dashboard, original brief, current working brief and decisions before proposing changes. Preserve the original source. When the client gives new instructions, record the change in the decision log and update the affected rooms.

At intake and on resuming an existing house, read or fill the homeowner’s [change preferences](skills/renovation-pack/references/layout-review.md#what-the-homeowner-is-willing-to-change) in the working brief and check room exceptions. Use these boundaries to decide which alternatives to model and when to ask. Carry the homeowner’s choice through the affected reviews.

Use the repo's renovation-pack skill for design work. Complete the relevant handover checks per room, attach real evidence and record the reviewed revision in its review.csv. A final AI image follows a reviewed, individually furnished Blender camera with the actual selected product variants checked. Dress the full selected room before the final camera, reconcile quantities and visible variants against the native objects and review the final AI photo beside that camera. An early AI styling concept is optional when the homeowner is still choosing the look. Keep rejected studies out of current presentations.

Keep private evidence, native models and issued packs in the named house's local folders. Include only the selected house in exports. When asked for project progress, report the first unresolved decision, what has been reviewed and what the homeowner can open.

Before recording a proposed CAD pass, inspect one coordinated plan showing the room's main activities in use at the same time as its circulation. Record a current `whole-room` finding and link that plan. Apply this to new and existing houses.

Apply the [living-design review](skills/renovation-pack/references/layout-review.md) to every house. Before furnishing, run `python house.py check-layout "House" "Room"` and inspect the linked evidence. Use the repository's FreeCAD and Blender skills for their respective handovers. A render hold pauses rendered cameras, AI images and their publication. An expressly CAD-only or all-visual hold also excludes Blender exploration. Respect the scope supplied by the homeowner.

Use the [agent workflow and architecture diagram](docs/agent-workflow.md). Drive native edits through live FreeCAD MCP or Blender MCP. Run deterministic build, placement and measurement functions through that connection. Run project setup and analysis of exported evidence locally. When disconnected, reconnect and inspect the document before retrying a mutation.

For furniture exploration run `python house.py check-study "House" "Room" --input-revision R3` with the actual shell revision. Return candidate placements to FreeCAD for the occupied layout test. Before a furnished camera or final image run `python house.py check-render "House" "Room" blender --input-revision R3` or use `final-ai`. Inspect the underlying evidence and homeowner instructions. For a new installation follow the [connector readiness checks](README.md#verify-the-design-tools-on-a-new-computer).

At each handover, compare the sources by purpose. A missing door in an AI reference does not authorise its removal. Keep observed fabric in existing CAD. If a proposed change to it or a consequential trade-off needs a homeowner decision, follow the [decision stops](skills/renovation-pack/references/layout-review.md#when-to-ask-the-homeowner), record the question and hold the affected proposal. Continue independent work on the retained baseline.

For a shared activity, inventory the intended positions in the room brief before checking the model. The room gate matches each declared activity-position ID to a current use check. For grouped furniture, verify count, spacing, functional fronts and the real outline of the shared object. State which interface performed the read-back.

When a room brief depends on seeing something from a particular seat, record the target and viewpoint and apply the [seated sightline check](skills/renovation-pack/references/layout-review.md#seated-sightlines). Review it alongside conversation, reach and routes before accepting the seating layout.
