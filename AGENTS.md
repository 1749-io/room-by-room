# Working on a house

Use the [skill routing table](CONTRIBUTING.md#route-a-request) to choose the owner of the next decision. For a standalone drawing, schedule or house ZIP, follow [pack delivery](skills/pack-delivery/SKILL.md). For paired existing and proposed brochures, use [property comparison](skills/property-comparison-pack/SKILL.md).

Use the `agent-evaluation` skill for every workflow evaluation. Follow the [handover cases and scoring guide](examples/agent-review.md) and record what the agent actually did.

## Start or resume the named house

For a new project, follow the root [intake and startup guide](README.md#start-a-project). Accept the homeowner's materials in their supplied form, fill the working brief from available evidence and ask only for gaps that affect the next decision. Use the [same review stages](README.md#design-and-review-stages) for every property.

Write in British English. Use the named house under `houses/` as the project root. Run `python house.py list` to locate one. For a new house, run `python house.py start`, supplying the original brief file if available. Use only this household's layouts, furniture, budget and decisions.

Open the house’s `CHECKLIST.md` at intake and on resume. Refresh it after any room review or survey return with `python house.py checklist "House"`. Keep the evidence in the room and survey registers and record homeowner acceptance explicitly. [Checklist workflow](docs/house-checklist.md)

Read the house dashboard, original brief, current working brief and decisions before proposing changes. Preserve the original source. When the client gives new instructions, record the change in the decision log and update the affected rooms.

At intake and on resuming an existing house, read or fill the homeowner’s [change preferences](skills/renovation-pack/references/layout-review.md#what-the-homeowner-is-willing-to-change) in the working brief and check room exceptions. Use these boundaries to decide which alternatives to model and when to ask. Carry the homeowner’s choice through the affected reviews.

On resuming, read `python house.py history "House"` alongside the dashboard and room reviews. Before producing or revising an output, use `begin-revision`, work in the printed private directory and `save-revision` with its inputs, change, reason, author, effects and next action. The save verifies a private whole-house backup before publication. Link the saved output at handover. Follow the [revision and recovery guide](docs/output-revisions.md).

Use the [worked examples](examples/README.md) to find a relevant replay or handover. Use the current house's brief, permissions and geometry for live decisions.

## Assign the decision and its owner

For a whole-house commission, start with the [shared decisions and dependencies](skills/renovation-pack/references/whole-house.md). For a UK alteration, use the [nation-specific consent enquiry](skills/renovation-pack/references/uk-consents.md) when it affects the decision.

Screen every new homeowner request, follow-up, substitution and returned measurement for an explicit or implied specialist question. Use the [request-to-study guide](skills/renovation-pack/references/specialist-design-tools.md#requests-that-trigger-a-specialist-study). Run the relevant permitted check with the evidence available. Record the deciding unknown and its owner when the evidence is insufficient. Return findings to the affected room, budget, order or programme and repeat its checks.

For a mid-study design question, run `house.py ask` against the open revision and use its validated inline prompt. At handover use the same check through `save-revision --ask`. When the answer depends on seeing a layout, route, finish or option, display a labelled image beside the question in chat. Show the affected seats, doors or surfaces and describe the practical difference in one sentence. If the question form takes text only, display the image in the conversation immediately before the form. Save the same image and description with the question. Use a checked CAD plan during a render hold. [Visual questions](skills/renovation-pack/references/homeowner-decisions.md#show-the-choice)

At each handover, compare the sources by purpose. A missing door in an AI reference does not authorise its removal. Keep observed fabric in existing CAD. If a proposed change to it or a consequential trade-off needs a homeowner decision, follow the [decision stops](skills/renovation-pack/references/layout-review.md#when-to-ask-the-homeowner), record the question and hold the affected proposal. Continue independent work on the retained baseline.

## Review the occupied geometry

Use the [agent workflow and architecture diagram](docs/agent-workflow.md). Drive native edits through live FreeCAD MCP or Blender MCP. Run deterministic build, placement and measurement functions through that connection. Run project setup and analysis of exported evidence locally. When disconnected, reconnect and inspect the document before retrying a mutation.

At the first CAD pass, record consequential unmeasured dimensions as editable working assumptions. Link the basis, relevant range, survey return and recheck in the house’s `cad-assumptions.csv`. Use the [FreeCAD workflow](skills/freecad-renovation/SKILL.md).

Run [route studies](skills/freecad-renovation/references/route-studies.md) behind the existing CAD reviews. Use the household's routine, occupied geometry and change permissions. Report a current pinch during an assessment. During design, try only permitted alternatives and rerun linked journeys before release.

Before recording a proposed CAD pass, inspect one coordinated plan showing the room's main activities in use at the same time as its circulation. Record a current `whole-room` finding and link that plan. Apply this to new and existing houses.

Review the room’s openings together. In the occupied CAD pass, check the leaf through its full movement, handles, nearby fittings and the [wall or glazing above the doorway](skills/freecad-renovation/references/opening-clearances.md#check-the-doorway-in-elevation). Repeat the room check against the reopened furnished model before issuing a planning concept or final camera. Keep a failed fit on hold and show the affected interface. During the usual photo review, inspect the head in views that show it. Record an outside-frame or obscured head with the other camera evidence. Keep the chosen framing when it already answers the brief.

When a room has a glazed roof or enough glazing to affect a household activity, start the [glazed-room review](skills/renovation-pack/references/glazed-rooms.md) when the room is first requested. Record tree and building shadows, seated glare, summer heat and winter cold before passing the occupied proposal.

For a shared activity, inventory the intended positions in the room brief before checking the model. The room gate matches each declared activity-position ID to a current use check. For grouped furniture, verify count, spacing, functional fronts and the real outline of the shared object. State which interface performed the read-back.

When a room brief depends on seeing something from a particular seat, record the target and viewpoint and apply the [seated sightline check](skills/renovation-pack/references/layout-review.md#seated-sightlines). Review it alongside conversation, reach and routes before accepting the seating layout.

Apply the [living-design review](skills/renovation-pack/references/layout-review.md) to every house. Before furnishing, run `python house.py check-layout "House" "Room" --input-revision R3`, substituting the revision of the actual CAD input, and inspect the linked evidence. Use the repository's FreeCAD and Blender skills for their respective handovers. A render hold pauses rendered cameras, AI images and their publication. An expressly CAD-only or all-visual hold also excludes Blender exploration. Respect the scope supplied by the homeowner.

Give every new or revised homeowner diagram a compact on-sheet key. Match the symbols and line styles on that particular sheet, name objects in household language and keep the key clear of the drawing. For a route, identify the origin, destination and who is moving. Keep a measurement detail focused on the object being measured. [Drawing and key checks](skills/renovation-pack/references/handover-gates.md#drawing-keys)

## Furnish and review a camera

For furniture exploration run `python house.py check-study "House" "Room" --input-revision R3` with the actual shell revision. Return candidate placements to FreeCAD for the occupied layout test. Before a furnished camera or final image run `python house.py check-render "House" "Room" blender --input-revision R3` or use `final-ai`. Inspect the underlying evidence and homeowner instructions. For a new installation follow the [connector readiness checks](README.md#verify-the-design-tools-on-a-new-computer).

Use the repo's renovation-pack skill for design work. Complete the relevant handover checks per room, attach real evidence and record the reviewed revision in its review.csv. A final AI image follows a reviewed, individually furnished Blender camera with the actual selected product variants checked. Dress the full selected room before the final camera, reconcile quantities and visible variants against the native objects and review the final AI photo beside that camera. An early AI styling concept is optional when the homeowner is still choosing the look. Keep rejected studies out of current presentations.

Review the colours together in every furnished room and record a current `room-palette` finding before final AI. Ask the homeowner about any consequential open choice, check each issued AI photo against its Blender camera and check the decorator schedule when issuing physical finishes. Follow the [renovation-pack colour workflow](skills/renovation-pack/references/colour-decisions.md).

Before issuing room photographs or assembling the house, apply the [photo quality and adjoining-room checks](skills/renovation-pack/references/photo-quality.md). Show the room in use and check the completed design through each visible opening.

Inspect visible window coverings from both sides, through other windows and in reflections. Register exterior cameras and check the curtain lining, blind position or uncovered glass against the owning room before issue. Follow the [photo evidence guide](skills/renovation-pack/references/photo-quality.md#window-treatments-across-photographs).

A furnished room normally continues from the checked camera through the final concept photo, side-by-side review and downloadable room pack. Continue routine stages without asking for a separate finish instruction. Record an expressly narrower commission or pause in the room brief. Keep purchase-only holds on the shopping schedule or in the [scoped product review](skills/renovation-pack/references/handover-gates.md#finishing-a-furnished-room).

## Issue the agreed output

Keep private evidence, native models and issued packs in the named house's local folders. Include only the selected house in exports. When asked for project progress, report the first unresolved decision, what has been reviewed and what the homeowner can open.

At handover, show the checked output. For feedback, invite the homeowner's reaction first, offer a relevant example or two and explicitly leave room to move on or pause. For a blocking homeowner choice, ask directly and explain what their answer changes. Follow their existing instructions and assign technical checks to the person who can resolve them. Use `house.py next` on resume and `house.py answer` to record their reply. [How to choose a handover question](skills/renovation-pack/references/homeowner-decisions.md#at-the-end-of-a-commission)
