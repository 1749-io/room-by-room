---
name: blender-interiors
description: Use live Blender MCP for unrendered furniture arrangement on a checked CAD shell and for product-matched furnished cameras after layout approval.
---

# Blender interiors workflow

For house work, save the scene, its dependencies and camera exports in the workspace printed by `house.py begin-revision`. Reopen and check the camera before `save-revision`, then link the saved files at handover. [Output history and recovery](../../docs/output-revisions.md)

If a viewport, product change or lighting study reveals a question about sightlines, solar exposure, fit, privacy or finishes, follow the [specialist request guide](../renovation-pack/references/specialist-design-tools.md#requests-that-trigger-a-specialist-study). Return evidence to the relevant owner and repeat affected camera and product checks when the design changes.

Use the live Blender MCP. Start with `get_addon_status` and `get_scene_info` including settings. Check the file, unit scale, collection and camera before editing. If unavailable, reconnect to the intended live application and confirm its state. Work in a named copy. Read the house brief, change preferences and holds when choosing the mode.

For a highly glazed room, carry the checked true-north rotation, obstruction assumptions and study times into any furnished camera. Use the occupied [glazed-room review](../renovation-pack/references/glazed-rooms.md) for comfort decisions.

## Explore furniture before a layout is selected

Return a moved chair, table or working envelope to the CAD route review before furnishing the chosen arrangement. Use the household journeys recorded in the affected rooms, including any shared route through an adjoining space. Keep protected pieces and building work within the homeowner's stated scope.

Run `python house.py check-study "House" "Room" --input-revision R3` with the shell’s actual revision. Where exploration is in scope, lock the transferred shell, verify a known length, two identifiable features and orientation, then move named, dimensioned furniture in a candidate collection. The [room asset library](references/room-assets.md) builds a candidate piece at its stated size and reads the size back. Try the actual household routine in overhead and eye-height solid viewport views. Keep architectural options in separate CAD files. A CAD-only request or hold on all visual work keeps the study in CAD. A render-only hold allows an otherwise authorised unrendered study.

Use deterministic placements and relationships through `execute_blender_code` where they help compare options. Retain IDs, units, origin, axes and per-item world coordinates and natural fronts when handing candidates back to FreeCAD. For meshes with a distinct seat, back and target, the [layout read-back helper](scripts/layout_readback.py) measures the three in evaluated world space. Send the reviewed function definitions and call through MCP in safe mode. For a single mesh inspect its actual geometry or documented local reference features. Reopen the saved study and check a top and reverse view. The occupied FreeCAD review decides whether a candidate can advance.

## Furnish and render the reviewed option

Before showing a concept in operation or issuing a furnished camera, compare the [opening clearance inventory](../freecad-renovation/references/opening-clearances.md) with the actual scene. Include any projecting geometry introduced in Blender and run the camera check. Show a confirmed clash as a diagnostic and return it to CAD.

Run `check-layout` and `check-render "House" "Room" blender --input-revision R3` through the house workbook using the actual input revision. Honour any visual hold. Transfer the selected native geometry in metres, verify dimensions, handedness, openings, levels and world transforms, and match the placements to the reviewed CAD plan. A poor reach, route or sightline reopens the layout check.

Dress the whole room after the layout and look are chosen. Reconcile the shopping list with item IDs, selected variants, quantities and object instances in the reopened scene, including out-of-frame pieces. Use reference-matched assets for purchases and distinctive retained pieces. Use simple library assets for incidental books and loose styling. The [room asset library](references/room-assets.md) supplies repeatable stand-ins at a stated size. One may represent a selected product only when it matches that product's distinctive form, with the remaining differences recorded in the product comparison. Include rugs, curtains, lights, artwork and accessories actually agreed for this room. Identify which camera shows each selected object or explain its normal concealment. If the look is open, an optional styling concept may precede sourcing. Any accepted new piece returns to the schedule and the editable scene, then to CAD when it affects fit.

Tag one representative object per purchased or reused unit with `furnishing_room` and `shopping_ref`. For a retail pair, use one tagged representative and inspect both pieces. Run [the quantity check](scripts/furnishing_readback.py) through MCP against the selected schedule, including zero quantities for omissions. Inspect any missing, extra or hidden item. Check product identity and camera visibility separately by eye.

Before releasing a furnished camera, run the [lighting and finish review](references/lighting-and-finishes.md). Save a same-camera lighting comparison and compare prominent product finishes in neutral light with their exact references. Then open the dressed room view and judge the wall, floor, furniture and accent colours together against the homeowner’s brief. Record a current `room-palette` finding with the brief and view. For a concern, identify where it appears, under which light and the smallest adjustment worth trying. Honour deliberate colour choices and refer consequential alternatives to the homeowner.

For a palette study, keep the selected product variants and lighting fixed across options. Consult `color-expert` for a colour choice or cast diagnosis and return the options to the renovation-pack workflow. Once an AI image exists, compare its colours with this exact camera and record the outcome before release.

Use named collections and repeatable cameras. Match the selected and reused shopping IDs, actual model or referenced reconstruction, variants, size, finish, count and distinctive features. Record local asset provenance and permissions. Check the full room and the named camera against the brief, with a reverse angle for hidden items. Render after the gate permits it. Supply the editable scene, reviewed camera image, product comparison and assumptions. The final AI stage takes that furnished image as its source after the product and render checks. [Blender MCP](https://github.com/ahujasid/mcp-for-blender)

Brief and frame the whole room and the features that matter in use. Record sightlines through doors, glazing and mirrors for the [photo and house-assembly review](../renovation-pack/references/photo-quality.md).

Before releasing a camera, verify wall-mounted items against architraves and door sweeps, and trace the leaves, hardware and framing of visible openings. Record the [architectural detail checks](../renovation-pack/references/photo-quality.md#architectural-detail-gate).

Before issuing a furnished concept or camera, compare the reopened scene’s door heads with the intended CAD elevations, including openings seen beyond the room. Run the [door elevation check](../freecad-renovation/references/opening-clearances.md#check-the-doorway-in-elevation).

Run the [fully dressed walkthrough](../renovation-pack/references/handover-gates.md#fully-dressed-walkthrough) against the reopened camera scene after placing all accessories.
