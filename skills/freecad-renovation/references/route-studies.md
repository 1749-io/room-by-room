# Checking a household journey

Start from what the household actually does. Identify the origin and destination, who or what travels, the occupied state and any protected furniture, rooms or building work. A buyer's baseline assessment ends with findings and viewing measurements. For a furniture brief, try permitted moves and keep protected pieces. For a renovation brief, compare only the building alternatives the homeowner has authorised. Permission to explore an option and selection for issue are separate decisions.

## Input from CAD

Save and reopen the named CAD revision through FreeCAD MCP. Export closed plan outlines in a single world coordinate frame in millimetres for the floor, walls, door leaves, furniture and working envelopes at the relevant height. Include floor holes, steps or impassable areas. Use a separate same-level study or a section for vertical travel. Keep the door moving, fully open and closed states distinct where they affect use. Attach the read-back, its units, the source of the chosen clearance and the approximate dimensions. Where scale or geometry is missing, ask for the deciding measurement before making a fit claim.

Run the analysis locally from the checkout. Install the route dependencies in that Python environment with `python -m pip install -r requirements-routes.txt`. The normal project starter is independent of these libraries.

Use a house-relative file ending in `.routes.json`. The following synthetic dining study shows the input format. Its dimensions are illustrative.

```json
{
  "revision": "R2",
  "units": "mm",
  "source": "rooms/dining/cad-readback.json",
  "authority": "decisions.md",
  "basis": "Shopping from the entrance with both rooms occupied. Width agreed for this comparison.",
  "floor": [[0,0],[6000,0],[6000,3000],[0,3000]],
  "obstacles": {"Sideboard": [[2200,500],[3200,500],[3200,1100],[2200,1100]]},
  "allowed_changes": {"Sideboard": "reposition"},
  "options": {"sideboard-east": {"Sideboard": {"translate_mm": [1400,0]}}},
  "journeys": {"carry-shopping": {"start": [600,1500], "end": [5400,1500],
    "width_mm": 750, "uncertainty_mm": 30}}
}
```

The baseline is the reference described in `basis`. State explicitly whether it represents the existing house or an already selected concept. For a saved export add `source_sha256` with the SHA-256 of the source file (use LF line endings for JSON, CSV, Markdown, SVG and plain text) so an in-place edit triggers a fresh check. The footprint format accepts an exterior coordinate ring or a GeoJSON Polygon or MultiPolygon with holes. Export the full connected set of rooms for a cross-room journey. Place endpoints where the person or load needs to stand. Check that an arbitrary start point or cropped study edge has not created the reported pinch.

The default scope permits assessment only. Obtain each object's permission from the house brief and room exceptions. A `reposition` permission allows translation and rotation in degrees about the object's centroid. An `alter` permission allows a replacement outline or removal using JSON null. A named null footprint in the reference can represent an authorised addition. Use a retained outer envelope with obstacles for wall and opening changes. A changed storey outline needs its own reviewed export. Keep protected objects out of the permission list. An option requires a house-relative `authority` file. Read the actual decision and conditions before modelling.

For each journey, set `width_mm` to the agreed width for the person or load and `uncertainty_mm` to the estimated overall width error. Zero tests the supplied model dimensions. Use `measurements` for outstanding facts that could reverse the result, including turns, thresholds, door operation and floor changes. Add `in_use` with named occupied polygons for people, equipment, open appliances or an area the routine must avoid. For an envelope that moves with furniture, supply `{"attached_to": "Sideboard", "outline": [[...]]}` using its baseline world coordinates. Give different routines their own named journeys. Use `max_loss_mm` only where the household or brief defines a permissible loss against the reference.

## Read the result

Run `python house.py check-routes "House" rooms/dining/occupied.routes.json --input-revision R2`. Add `--option sideboard-east` for an authorised study. Add `--json` for the route centreline, pinch coordinates, nearby object and length for the CAD overlay. The command assesses the model without selecting an option. Set `review_option` in the input when a recorded choice is ready for the proposed-layout gate. Link the house-relative decision under `selection` for that option, including any delegated choice. Its default is `baseline`.

Shapely subtracts occupied geometry and tests whether a circular clearance envelope can travel between the endpoints. The inset is slightly conservative at rounded corners. NetworkX finds a distance-weighted route through adjacent triangles inside the remaining space. The resulting path is straightened and its continuous clearance checked. `tested_mm` is the largest whole-millimetre model width found by the conservative search. `path_clearance_mm` and `beside` describe the particular drawn path, which may favour a shorter walk. Inspect that path in context. A planar disc can establish a clear approach. A walker, wheelchair, long load or stair journey may also need turning, height, slope and threshold checks.

Declare the household routine once in the room’s `route-journeys.csv` with a stable journey ID. For a shared journey, use the same house-unique ID in each room it crosses. Search the room inventories for that ID when an endpoint, obstacle or threshold changes and review the affected rooms on the coordinated revision. This carries the obligation to recheck into later revisions. An older room can add the register with `prepare-reviews`. When the brief genuinely removes a routine, record the homeowner decision and update its inventory. Use the existing `journey` row in `layout-checks.csv` for each consequential modelled route. Put the study path in `evidence` and `route:<journey-name>` in `check_id`. Add that column to older registers when first linking a study. The normal proposed-layout gate reruns each linked journey at its reviewed revision. Other existing journey evidence remains usable. A `restricted`, `measure` or `review` result holds a proposed pass for that journey. A baseline diagnostic can report any of these findings and still complete an assessment. Overlay the result on the whole-room plan alongside sightlines, reaches and operating zones.

If a proposed change creates a conflict, first try the smallest permitted adjustment and recheck both ends of the journey. When choices within scope run out, describe the practical limitation. Ask which use takes priority only when a decision is needed. A homeowner can retain a known limitation. For that named journey record `retained_constraint` with the exact `option`, a `reason` and the house-relative `decision` file. Its diagnostic remains restricted. The concept gate can carry it only when the baseline already fell short and the change preserves or improves the tested width. A new loss or an unresolved measurement stays open. Keep survey-dependent fit and accessibility questions open for their intended use.
