---
name: blender-house-walkthrough
description: Make a first-person Blender house tour when someone asks to experience walking through a home, sitting down or looking around from a particular place. Activate only on a request for that experience.
---

# Blender house walkthrough

Follow the journey the homeowner wants to experience. “Take me from the hall to the sofa and let me look into the garden” gives the start, destination, seat and view. Use those details directly. A request to finish a room pack, test an occupied route or produce a brochure uses its usual workflow. The routine fully dressed walkthrough remains a clearance check.

## Set up the visit

Identify the named house, existing or proposed scheme, current reviewed scene revisions and any visual holds. Use the house checklist, history, room reviews and decisions. For each room shown, check the underlying furnished evidence and run the repository’s `house.py check-render "House" "Room" blender --input-revision REV` with its actual input revision. Honour holds, including for adjoining rooms visible through openings. If a leg depends on held or missing geometry, identify that leg and show only the available, permitted extent. Keep distinct scenes as labelled chapters until their doors, levels and orientation register in one model.

Start a private output with `house.py begin-revision`. Through live Blender MCP, inspect the active file, units, scene and camera. Work in a copy in the printed revision directory. Preserve the reviewed furniture, lighting and cameras. Add a dedicated tour camera and timeline markers named for recognisable places or actions. Use the repository’s `skills/blender-interiors/SKILL.md` for furnished-scene checks.

## Walk, arrive and sit

Use the repository's [FreeCAD household route study](../freecad-renovation/references/route-studies.md) for every walking leg, including previews. Run `python house.py check-routes "House" <house-relative.routes.json> --input-revision REV --json` to plan the route. Use the reviewed body or load width, occupied obstacles and agreed tolerance. Register both sides of each doorway in the same floor coordinates. Include the actual posed leaf, handles and jambs. Inventory each transition between rooms, including either side of an edit.

Before encoding, export the evaluated walking body's floor positions from the final playback timeline in millimetres. Use each journey's `walked_path_mm` array with its matching start and end, and rerun the command with `--require-walked-path`. This option exits unsuccessfully if any journey lacks a recorded path or fails to fit. It checks every connecting segment of this particular trajectory. Sample eased curves adaptively between frames and include their remaining deviation in the clearance margin. At a moving door, split time into intervals and include the leaf and handle swept during each interval. Wait outside the swing, show the opening, then walk through the checked aperture. Cross-check against the reopened scene used for the film. For stairs check tread support, risers and headroom in section. At a seat check the approach, the turn and the seated body separately. A cut between sets cannot certify a crossing.

Release the MP4 only when every filmed walking leg returns `fits` and each vertical or operating transition has matching evidence. Save the source revision, track, door states, time or frame ranges and results with the film. On a failure record the time and blocking object, fix the path or permitted action and repeat the checks on the exported movement. An unresolved leg can be shown in a separately requested diagnostic.

* Trace the journey on the actual walkable floor, through clear openings and around occupied furniture. Follow the floor elevation on stairs and landings. Show a door in a verified usable position or animate its checked swing.
* Keep a level horizon, a consistent natural field of view and an unhurried pace. Turn towards a doorway before crossing it. Ease starts and stops, and leave enough time at a destination to understand the view.
* For a seated visit, approach from the accessible side, turn into position and lower the camera to the seated eye point above the actual cushion. Use the household’s standing and seated eye heights where supplied and record any assumed heights. Hold the requested gaze and let the real sill, table, other furniture or seat back obscure the view where they do. Stand up and resume walking if the route continues.
* Preview the interpolated motion, especially corners, door jambs, stair soffits and the turn into a seat. Check the space occupied by the person as well as the lens. Correct camera overshoot or clipping and replay the section. If the layout itself blocks the journey, stop there and record the obstruction for the owning room.

## Give the homeowner the visit

For a guided visit, export a playable MP4 and retain the editable camera in the private Blender file. For a request to steer freely, provide the prepared Blender scene with a starting viewpoint, named seated viewpoints and short instructions for entering Walk Navigation, looking around and returning to a saved seat. Test that interaction in the reopened scene.

Watch the issued film from beginning to end or try the requested controls. Verify doorway continuity, seated sightlines, visible adjoining spaces and any disclosed gaps against the source revision. Save the output with `house.py save-revision`, record the route, source scenes, assumptions and review result, and link the saved deliverable. Invite feedback on a specific moment in the journey.
