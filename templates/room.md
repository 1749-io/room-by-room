# {{room}}

Where glazing or a glazed roof drives use, record the standalone line `Glazing review: required`. Identify the activity, viewpoint and times of use. The layout register then requires current external-shadow, seated-glare, summer-heat and winter-cold findings. Conservatories, sunrooms, winter gardens and orangeries trigger these automatically.

## How this space should work
Before placing furniture, use [the layout register](layout-checks.csv) to record spatial preferences (`intent`), everyday activities (`use`) and connected routes (`journey`). Name the people, starting and finishing points, furniture or doors in use, and what would count as a workable result. For a shared route, identify the adjoining room. After modelling, record the observed result, revision and house-relative evidence path. Keep unresolved checks on hold and identify the measurement or decision needed.
Describe its users, furniture and connections. Record what stays and what changes.

For a modelled route, enter the household routine once in [route-journeys.csv](route-journeys.csv). Link the current `.routes.json` CAD study on its journey row and use `route:<journey-name>` as its check_id. Record endpoints, occupied state, width basis and any deciding measurement. Recheck affected cross-room journeys after a change. Keep baseline observations and the selected proposal identifiable.

In [activity-positions.csv](activity-positions.csv) list each intended position for a shared activity, with a stable check_id. Use one matching ID on a current use row in the layout register for each position. Give an annotated drawing or other checkable evidence. On an older register append the check_id column if needed. Record exceptions and resolve consequential unknowns in the brief.

If a particular view matters, name all intended seats, their natural fronts, the target and its fixed reference. Review the sightline with the room occupied and someone using the main route. Attach the relevant CAD plan and section to the use check.

## Local preferences

Inherit the house limits in the working brief. Record any exception with the item or intervention, what the agent can explore, the conditions, the homeowner's wording and date. Keep option selection in the house decision log. At a conflict, test permitted changes first and ask a focused question if the remaining choice is consequential.

## Model handover

Link the actual FreeCAD or Blender document and revision, state the live connector and units, and record the geometry read back after reopening. For a furniture study, identify the shell and candidate and record how its placements returned to CAD. Record whether the homeowner has paused renders, all visual work or a particular option.

## Whole-room plan

Link one CAD plan for the current revision showing people, the things they need to use or reach, and a route while those activities are taking place. Include any viewing or door conflict that matters to this room. Record one `whole-room` row with the simultaneous scenario, the result and a house-relative path to the drawing. Hold the layout if the activities compete.

## Fit and finish
List the moving assemblies, hardware and nearby fixed projections with their working heights, full travel and survey tolerances. Keep a current opening clearance report for CAD and for the furnished scene.

For existing CAD, link the source plan, photograph checks and a cutaway or section. List consequential fixed features and unknown measurements. For proposed CAD, link the overlay and record the tightest clearance for the way the room will actually be used.

Record dimensions with their sources, door swings, occupied clearances, finishes, storage, lighting, power, ventilation and accessible use.

## Items to see in the design
List shopping IDs, selected variants, quantities, reused pieces and any shared items. Link product photographs and model objects. Mark unsized allowances. For the final furnishing pass reconcile ID, variant, quantity and native object for each selected or retained piece. List which camera shows it, incidental dressing and the result of comparing the final AI image with the furnished camera.

Record the same-camera lighting comparison and a neutral finish review for each prominent selected product in [finish-checks.csv](finish-checks.csv). For a room without named products, review its specified architectural finish. Use `lighting` and `finish` rows with the current revision, subject, reference, house-relative image or PDF evidence, finding and result.

## Review with the homeowner

A reviewed furnished camera normally leads to the final room photo and downloadable pack. If the homeowner expressly limits the issue to the Blender views, record their dated instruction with the standalone line `Furnished deliverable: views only`. Use `Furnished deliverable: paused` for an explicit pause.

List fixed colours and open choices. Before final AI add a `room-palette` row for this revision with the brief or decision path, furnished view and finding. Explain how the colours work together in the light shown. Locate any concern and give the smallest adjustment worth trying. For a consequential open choice, add a `palette` row with the homeowner’s question and link the decision once selected. For each final photo add `ai-colour` with the reviewed camera as its source and the actual AI image as evidence. In [decorator-finishes.csv](decorator-finishes.csv), record the selected surfaces and any outstanding samples when decoration is in scope.
At each handover, record any conflict between property evidence, the brief and inspiration images. Show the retained layout, what a change would gain or cost, who needs to decide and which checks must wait. Link the house decision log and carry its answer to the next revision.
Link the current plan, individual furnished camera, product comparison and final AI image. Record the decision needed and any dependencies.

The adjoining review.csv records pending, hold or pass for each handover. For a pass, enter the revision, reviewer, finding and an evidence file path relative to the house. Use the same issue revision throughout. Reopen affected reviews when a design or product changes.
