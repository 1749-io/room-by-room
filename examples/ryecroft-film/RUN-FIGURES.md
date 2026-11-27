# Where every figure in the film comes from

The house is fictional. The tools and their results are real: each figure was produced by the named tool on 27 November 2026 and saved in a revision of the example house. All paths are under that house's record, `houses/ryecroft/`, which is private to the run and is not in this repository. This table applies to version 7 of the film. The final design is revision R7 (R6 with one opening report corrected; pictures made in R6 are carried into R7 unchanged).

| On screen | Value | Source |
| --- | --- | --- |
| Room sizes | Dining room 3.65 × 4.10 m, kitchen 2.55 × 3.00 m, conservatory 3.65 × 2.50 m | The agent's plan (`source/plan/plan-basis.md`), read back from `revisions/EXISTING-R1/outputs/models/existing-readback.json` |
| "It carries the floor above: a beam is needed" | Yes, on the assumptions made | `revisions/OPENING-R1/outputs/structure/beam-needed.json` |
| Clear opening, span | 2.68 m, 2.83 m | `revisions/OPENING-R1/outputs/structure/case.json` |
| Trial beam | 203 × 133 UB | `case.json` |
| PyNite, CalculiX deflection | 2.30 mm, 2.51 mm | `revisions/OPENING-R1/outputs/structure/verified-results.json` |
| Stress at mid-span | 59 MPa (58.8 PyNite, 59.2 CalculiX) | `verified-results.json` |
| Route A, route B | 756 mm at the kitchen door, 895 mm with the doorway widened | `revisions/ROUTE-R1/outputs/routes/kitchen-door.result.json`; 895 mm again in `revisions/R7/outputs/routes/carry-shopping.result.json` |
| "825 mm is needed to be sure" | 750 mm person plus 75 mm model uncertainty | `revisions/ROUTE-R1/outputs/routes/kitchen-door.routes.json` |
| Tallest trees | 18 m (group T2) | `revisions/CONSERVATORY-R1/outputs/site/site-study.json` |
| Low sun in view | 15:40 to 16:30 on 21 September, chair on the kitchen side | `site-study.json` |
| December | No direct sun on the seat | `site-study.json` |
| As it stands | 35 °C peak (35.3), 85 summer hours above 28 °C, 7.1 °C winter average | `revisions/CONSERVATORY-R1/outputs/comfort/comfort-results.json`, case 1 |
| New roof and vents | 30 °C peak (30.1) | `comfort-results.json`, case 5 |
| Choice sheet figures | 21 and 85 hours above 28 °C, 8 hours rebuilt, 16 °C felt, 1,631 kWh | `comfort-results.json`, cases 1, 4, 8 and 9 |
| Rebuild: "new low-energy glazing", "150 mm of roof insulation", "rooflight and heater" | The comfort study's assumed fabric (glazing U 1.2, 150 mm PIR in the roof), built as 12 steps in the live FreeCAD session | `revisions/R7/outputs/views/cad-build/build-log.json` and the run's comfort script |
| After: "Winter: 16 °C on average, heated" | 16.2 °C felt, December to February, 09:00 to 22:00 | `revisions/R7/outputs/climate/after-all-year.json` |
| After: "Hot days: 29 °C peak, was 35" | 29.3 °C against 35.3 °C | `after-all-year.json` |
| After: "8 hours above 28 °C, was 85" | 8 against 85, June to August, 09:00 to 22:00 | `after-all-year.json` |
| After: "Between 16 and 28 °C for 90% of waking hours, up from 39%" | 4,592 against 1,971 of 5,110 hours a year, 09:00 to 22:00 | `after-all-year.json` |
| After: "About 1,630 kWh of heating a year" | 1,631 kWh | `after-all-year.json` |
| Listing card: "Wren rattan armchair", "740 × 790 × 820 mm · £329", "hazelandthrush.example" | A listing invented for the example: the shop, chair, price and link do not exist | `revisions/R5/outputs/listing/listing.json` |
| Shopping list: "Armchair × 2, £329 each", "740 × 790 × 820 mm", "£658 on the list" | The listing's figures on the shopping list; 2 × 329 = 658 | `shopping.csv` row C01 |
| "Modelled at that size" | The chair built in Blender measures 740 × 790 × 820 mm | `revisions/R7/outputs/scene/conservatory-seat-readback.json` |
| Sliding doors: "Doorway 1,540 mm clear" | 1,540 mm between the parked leaves, measured in the reopened FreeCAD model | `revisions/R7/outputs/models/proposed-readback.json` |
| Sliding doors: "130 mm behind each armchair" | 129.7 mm from each leaf's travel to the armchair | `proposed-readback.json` |
| "Dining room 3.65 m, same as CAD" | 3.65 m, 0.005 mm worst difference over 45 objects | `revisions/R7/outputs/scene/transfer-readback.json` |
| "20 items placed" | 20, with no discrepancy against the schedule | `revisions/R7/outputs/scene/scene-readback.json`, `shopping.csv` |
| "Every chair faces its table or the garden" | All rows pass | `revisions/R7/outputs/scene/chair-facing-gate.json` |
| IFC | IFC4, 45 elements, metres, 3.65 m reads back | `revisions/R7/outputs/ifc/Ryecroft proposed.ifc`, reopened with IfcOpenShell |
| Programme | 42 working days on site (8.4 weeks), 33 without a kitchen (6.6 weeks) | `revisions/R7/outputs/programme/programme-summary.json` |
| "6 chairs, 2 pendants, fireplace kept" | Counted in the photo against the camera | `revisions/R7/outputs/final-ai/dining-room/dining-room-review.md` |
| "2 rattan armchairs, sliding doors, level floor" | Checked in the photo against the camera | `revisions/R7/outputs/final-ai/conservatory/conservatory-review.md` |
| "the garden follows the model: lawn, hedges, trees" | The garden in the scene, and the review of the photo against it | `revisions/R7/outputs/scene/garden-readback.json`, `final-ai/kitchen/kitchen-review.md` |
| Pack | Room review, drawing, shopping schedule | `revisions/PACK-DINING-R7/` |

## What is drawn for the film, not produced by the run

- The opening chat between Hannah and James, the listing card and its "view the listing" link. There is no property listing.
- The Codex window and the clone bar. The run was driven by Claude Code; Codex made the pictures.
- James's message with the armchair listing, and Hannah's asking for sliding doors. Both requests were written for the film and are recorded in `decisions.md`. The armchair listing is fiction: the shop, the chair, the price and the link do not exist, and the link uses the reserved `.example` domain. The film does not say so on screen. This page and the house record do (`shopping.csv`, `revisions/R5/outputs/listing/listing.json`).
- The armchair's product picture: made by Codex's image tool from a chair the agent modelled in Blender.
- The caption on each live-build frame, taken from the build log.
- The chat lines where the buyers answer. The answers were written for the film and are recorded in the house's answers and `decisions.md`.

## Tools shown, all of which ran

FreeCAD through its MCP add-on, FreeCAD FEM with Gmsh and CalculiX, PyNite, Shapely, NetworkX, QGIS, pvlib, EnergyPlus, Blender through its MCP add-on with Sun Position, IfcOpenShell, Codex's image tool, and `house.py`.

Not run, and not shown: TechDraw, OpenProject, the colour adviser.

## Image calls

Fourteen calls to Codex's image tool. The film shows four of them: the armchair's product picture (call 9, R5) and the dining room, kitchen and conservatory photos made in R6 (calls 12, 13 and 14). The ledgers are `final-ai/image-calls.md` in `revisions/R2` to `R6`.
