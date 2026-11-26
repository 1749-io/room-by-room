---
name: pack-delivery
description: Issue reviewed rooms, drawings, shopping, homeowner, architect and buyer editions, decorator finishes, editable costs and programmes individually or in an offline house pack.
---

# Pack delivery

Read the commission and identify the recipient, decision, room and requested components. Use `room-review` for browser and print, `drawing` for a forwardable PDF and `shopping` for a filterable workbook and CSV. Any combination can issue. Follow the [workflow diagram](../../docs/pack-delivery.svg) and [worked example](../../examples/component-pack/README.md).

Adapt the [room request](../../examples/component-pack/request.json) in the named house. Use the exact registered room, house ID and source revision. Give the reader the decision, limitation and next owner. For a drawing, choose the evidence in the existing or proposed CAD row. A passed proposed-layout check can supply an alternative drawing via `sheet_source`. For a multipage source, set its one-based `sheet_page`. Inspect the source key, scale bar, opening movements and labels at final print size. An enlarged or reduced drawing needs a scale bar or a diagrammatic qualification.

A room commissioned as a CAD review can finish with the checked drawing. Choose `room_scope: furnished` for a furnished room. This requires its handover gate and photo reviews and carries the checked camera and final photo pairs, including corrections. Confirm the room brief still authorises issue. The shopping component takes all matching room items from the house shopping register, including retained and purchase-held items. Check variants, quantities and purchase restrictions in the actual workbook.

When a shopping row names several rooms separated by a slash, the output shows the source rooms and their total quantity. The room quantity and cost are left open with an allocation hold. Confirm the split in the source register before a room-level order.

1. Begin a revision with `--pack-request <house-relative-file>`. This freezes the request and applicable source registers. An inherited design revision can supply evidence.
2. Run `plan-pack HOUSE ISSUE`, then `build-pack HOUSE ISSUE`. Read the file list and any named source hold. Build stages a private envelope in the draft and prints the reader's entry point.
3. Extract the ZIP elsewhere, disconnect the browser from the network and open `Start here.html`. Also open each commissioned component independently. Check what this particular reader will use, including the print layout or workbook filters. Run `check-pack HOUSE ISSUE --reviewer NAME --finding "What was checked in the extracted files"`.
4. Use `save-revision` with the usual change, reason, author, effects and next action. It rechecks live evidence and the receipt before the verified backup and publication. Share the saved component file or ZIP. The house checklist links the latest saved issue for each audience, room and selection.

For a full house edition use the [house request](../../examples/component-pack/house-request.json). Name each registered room and the saved source issue for each commissioned component. The builder checks audience, current evidence, room coverage and the original reviewed bytes. Return a failed room to its owning review, then build a fresh issue. The existing [formal photographic assembly](../renovation-pack/references/photo-quality.md) and [property editions](../property-comparison-pack/SKILL.md) retain their respective release routes.

## Audience editions

Before reusing a drawing or photograph, apply the [design and visual release check](../../docs/visual-release.md) for its actual purpose and scope. The room, audience and house builders carry those reviewed placements into their issue manifests.

Use the [audience request, copy templates and replay](../../examples/audience-packs/README.md). Build only what the recipient commissioned. Carry the priorities, options, costs and unresolved checks across from the house records. Record the publishable source or date beside each statement. Follow the [audience content guidance](../renovation-pack/references/deliverables.md) for the scope of the particular appointment or viewing.

- **Homeowner presentation.** Choose reviewed room issues in presentation order for each room and include the applicable shopping issue. Check the editable text, room evidence, daily use, options, costs and next decision in PowerPoint and its print PDF.
- **Architect pack.** Select each commissioned drawing issue, including existing and proposed sheets, levels and details where relevant. Open the bound PDF, check the title blocks at print size and follow every relative path in the drawing register to the forwardable original. State the survey status, scope, budget, responsible professional and next return.
- **Buyer brief.** Describe the purchase scenario and the evidence available for the viewing. Record works and acquisition assumptions, outstanding prices, timing and checks with their owners. Inspect the printable brief and reconcile priced items with the issued schedule. Record any private figures only in the copy cleared for that recipient.

Set `share_with` only where the commission authorises an additional named recipient. Household shopping sources, appointment notes and buying figures each retain their own source or edition permissions. To assemble the full pack, add the saved edition IDs to the house request's `editions` mapping. Inspect the actual extracted copies and record the reader finding before saving.

## Trade schedules

Choose a single `schedule` profile from the [Alder Cottage requests and replay](../../examples/trade-schedules/README.md). Record who may receive that schedule. Use the normal plan, build, extracted reader check and revision save. Incorporate a saved schedule in a house request through its `editions` mapping.

- For **decorator finishes**, name the rooms, finish revision and commissioned surfaces. Use the room's decorator register and the recorded sample approval or finish instruction. Read the named colour, code and sheen against the approved surface. Recheck the linked evidence before issue.
- For the **cost schedule**, map each authorised budget scope to the base, a named option or an exclusion. Trace any linked shopping IDs, VAT basis, fees, contingency and unpriced work. Reconcile the low and high totals. Open lines keep the corresponding total open.
- For the **programme**, use the house task register, a forecast start and the commissioned tasks. Include each predecessor, responsible owner, current holds, occupancy or service impact and any payment or decision date. Change a duration in a working copy and check the downstream forecast.
