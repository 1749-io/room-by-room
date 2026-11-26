# Photographing a room and its neighbours

Brief the photographs before setting cameras. Give the whole-room view enough context to read the layout and show each feature or operating condition that materially changed the design. Use one view for several purposes when they are actually visible. Choose another camera or time of day when light, framing or an obstruction hides the decision. Open every delivered photo at presentation size beside its own furnished camera and product references.

Record the framing, scale, exposure, colours, actual product identity, operating state and architectural openings. Look through doors, glazed partitions and mirrors. Name which room is visible and compare the finishes, furniture and opening with that room's reviewed camera. At room-concept stage, label a visible provisional room in the homeowner presentation. At whole-house issue, each visible room needs its current completed design. A garden view can be identified as indicative landscape. A closed glazed door can still show the next room. Keep the true architectural opening in the image.

## Architectural detail gate

At the native camera review, inventory wall-mounted objects next to openings, internal portals and visible door or window assemblies. Include partly cropped leaves, mirrored openings and glazed partitions. For each artwork frame, measure the shortest signed clearance from the complete object to the architrave and swept leaf in the model. Check the hanging location on solid wall. If perspective hides the clearance, inspect a wall elevation. Do this before generating a final photograph.

At final photo review, compare each visible detail at full resolution in the native camera and final image. Trace glazed leaves from head to threshold, reading each hinge, meeting stile, track, handle, rail and fixed pane. Compare leaf count, handedness, depth and operating state to the native opening schedule. Where lines coincide, use a reverse or oblique native view to resolve them. A plausible camera match can reproduce a modelling mistake. Return an impossible native assembly to CAD or Blender; regenerate a photograph that introduced the defect. An ambiguous result stays on hold.

In the brief declare `architectural_details` with two lists, `wall_mounts` and `openings`. Name every relevant object, including all entries already declared in the internal opening inventory. Empty lists are appropriate only when the inventory is clear. Each photo supplies both maps keyed by those same names. Each entry records visibility and a finding. Visible entries also require a pass and two normalised [left, top, right, bottom] inspection regions, one in the camera and one in the photograph. Mark the object plus its nearest edge or trim. The machine checks coverage and consistency. The reviewer inspects the geometry and pixels.

```json
{"wall_mounts":{"framed print beside door":{"visibility":"visible","finding":"Frame and architrave remain separate in the elevation and photograph.","result":"pass","camera":[0.11,0.22,0.36,0.65],"photo":[0.12,0.21,0.37,0.65],"model_clearance_mm":32,"photo_clear_of_opening":true}},"openings":{"glazed doorway":{"visibility":"visible","finding":"Meeting stiles continue to the threshold; the handle is on the opening edge.","result":"pass","camera":[0.4,0.1,0.8,0.9],"photo":[0.41,0.1,0.81,0.9],"model_leaves":["left hinged open","right fixed"],"photo_leaves":["left hinged open","right fixed"],"continuous_frame_and_hardware":true}}}
```

Record a homeowner-reported defect immediately in the affected room's `photo-defects.csv` with columns `photo_sha256,finding`. Use the exact issued image hash. The room check and comparison builder reject these pixels even if the former issue passed. Retain the finding when reviewing a new image. The corrected pair must pass independently. When using a copied asset folder outside the library, pass the named house using the comparison builder's `--house` option.

## Evidence files

For a one-room commission, an adjoining room can lie entirely behind every issued camera. In the photographic brief, keep the opening in the inventory and set its destination to an object with `outside_commission` (the adjoining room slug), `reason`, `reference` (a framing image or drawing in the review outputs) and its `sha256`. Record `outside-frame` and the finding in each photograph. If the opening enters any frame, register the adjoining room and use the ordinary sightline review. Registered rooms always use their normal room slug.

In the revision outputs, write `photo-reviews/<room>-brief.json` and `photo-reviews/<room>.json`. Include both files in the downloadable room pack. The brief names an evidence basis, a map of required views with a `whole-room` entry and at least one design-specific purpose, and a map of internal sightlines to room slugs. Inspect the room brief, registered plan and sightlines when preparing it.

```json
{"architectural_details":{"wall_mounts":[],"openings":["glazed door"]},"windows":{},"basis":"Room brief and checked plan, including the view through the glazed door","views":{"whole-room":"Show the furniture relative to the entrance","reading":"Show the reading light reaching the book"},"openings":{"glazed door":"hall"}}
```

The review names the room and revision. Each entry in `photos` matches a passed `ai-colour` photo and camera. Paths are relative to revision outputs. Record their SHA-256 digests. Use the fields below for each entry.

```json
{"architectural_details":{"wall_mounts":{},"openings":{"glazed door":{"visibility":"visible","finding":"Both meeting edges and the handle remain aligned.","result":"pass","camera":[0.4,0.1,0.8,0.9],"photo":[0.41,0.1,0.81,0.9],"model_leaves":["left hinged open","right fixed"],"photo_leaves":["left hinged open","right fixed"],"continuous_frame_and_hardware":true}}},"window_treatments":{},"photo":"Reading.png","camera":"Reading-camera.png","photo_sha256":"<digest>","camera_sha256":"<digest>","shows":["whole-room","reading"],"reviewer":"Reviewer name","result":"pass","composition":"The door, reading seat and lamp are all legible","products_and_operation":"The selected task lamp lights the book at reading height","light_and_finish":"Fabric detail is visible beside the lit shade","architecture":"The glazed divider retains both panels","opening_inspection":"The hall is visible through the left panel","openings":{"glazed door":"visible"},"visible_rooms":[{"room":"hall","through":"left glazed panel","status":"matched","comparison":"Hall floor, console and trim agree with its reverse camera","revision":"HALL-03","reference":"Hall-reverse.png","sha256":"<digest>"}]}
```

Use `visible`, `occluded` or `outside-frame` for every declared sightline. Use an empty list for `visible_rooms` only when the adjoining rooms are out of sight. A `provisional` neighbour needs a named room, sightline and explanation. Include that limitation in the room pack. The combined issue requires a matched photograph or furnished camera listed in the current adjoining room's photo review.

## Window treatments across photographs

Before framing a room, walk the model from the intended viewpoint. Inventory the windows that can show a curtain, blind, shutter, privacy glass or an uncovered opening. Include views through a second window and in mirrors. Identify each opening by position and owning room. A closed blind may hide the room while its outside face is plainly visible. Record the intended daylight or evening state in the brief.

Add a `windows` map to each room photo brief and a matching `window_treatments` map to each photo review. Use empty objects when the reviewed brief has no applicable windows. For each opening record its visibility and the visual comparison. For `occluded` or `outside-frame`, explain exactly what hides it. For `visible`, check the type, stack or drop, open/closed/slat position and outside-facing fabric, lining or glass against the owning room's current design. Inspect the photograph alongside the camera and room evidence at presentation size. A listing photograph establishes the opening but may show a former occupant's blinds.

```json
{"windows":{"upper right front":"study"}}
```

```json
{"window_treatments":{"upper right front":{"visibility":"visible","status":"matched","treatment":"lined curtains","state":"open, stacked both sides","outside_face":"ivory lining","comparison":"The two pale stacks expose the centre mullion, as in the reverse camera and lining schedule.","revision":"STUDY-02","reference":"revisions/STUDY-02/outputs/Window-detail.png","sha256":"<digest>"}}}
```

Use `status: provisional` and a `follow_up` naming the unknown and its owner where the treatment, lining, room assignment or view is unresolved. Show that limitation beside the concept photo. For a new visible mismatch, correct the image or camera and repeat the comparison. A provisional observation holds the combined house issue. A visual pass records a reviewer's judgement against specific files. It does not perform pixel recognition.

### Drive, garden and other exterior cameras

Before making standalone images, list each current photo and opening in the house's `exterior-views.csv`, with columns `revision,photo,opening,room`. Register passage and return views too. For a house issue with no exterior photographs retain the header-only register as the explicit inventory. For a replacement issue point the live register at the new revision and preserve the original in history. The saved review preserves the opening inventory used for each camera.

In the revision outputs create `exterior-window-review.json` with `revision` and a `photos` object keyed by photo path. Each entry records its `openings` map from the register and contains `camera`, `camera_sha256`, `photo_sha256`, `reviewer` and `window_treatments` as above. Use paths relative to those outputs for the camera and photograph and house-relative paths for source-room evidence. With the homeowner-facing presentation, identify day/night state and any provisional openings.

Run `python house.py check-exterior-photos "House" --input-revision R3` on the draft. Saving rechecks the registered views. Before combined handover, `check-house-photos` rechecks the live register, camera and source evidence and rejects provisional entries. Revisit every affected facade, return and reflected view when a room's window treatment changes.

## Assembling the house

Run `python house.py check-room-photos "House" "Room" --input-revision R3` on each room before release, using its actual revision. Run `python house.py check-house-photos "House"` to see all outstanding rooms and sightlines. Once clear, begin a separate revision and run `python house.py pack-house-photos "House" ISSUE`. This checks every registered room and creates the combined room-packs ZIP. Saving the revision rechecks the ZIP against the current room packs. Historic concept packs keep their original review status. Reissue their photographs against the current brief before including them in a final combined pack. A selected-room gallery remains a progress deliverable.

### When two rooms show the same doorway

For a visible opening into another commissioned room, mark the adjoining view provisional until both sides have been compared. Furniture and finish matches cover only part of that comparison. Inspect the shut leaves, their operating state and the section at the head from both rooms.

For a whole-house match, add an entry under `shared_openings` in the source room's photographic brief. This example uses the name from the brief's `openings` map.

```json
{"shared_openings": {"garden partition": {"kind": "doorway", "id": "garden-link", "mirror_x": true}}}
```

Use one stable physical doorway ID and leaf IDs in both rooms. Record `shared_opening` on every associated leaf in each room's saved CAD and furnished opening reports. For example, the dining-side section can carry `{"id":"garden-link","leaf":"garden-end","adjoining_room":"sunroom"}`. Use `dining` as the neighbour on the sunroom side. Local model object names can differ. Measure at the same plane in the shared construction, from the shut leaf top to the same physical partition top. Set `mirror_x` to true when the horizontal section axes run in opposite directions. The house check compares field dimensions and the areas occupied by air, glazing and solid material across each leaf. The comparison uses the current registered native files, including saved opening corrections.

Where the sightline genuinely passes through fixed glazing, an open passage or a reflection, use `fixed-glazing`, `open-passage` or `reflection` as the kind and give a specific `basis` for the classification. A glazed operating door is a doorway. Classify the physical opening during camera review. An outside-frame doorway needs its normal framing evidence. A missing section or unresolved fit keeps the affected combined view provisional. Existing standalone photographs retain their own review scope.

Passing these checks means the photo evidence and the reviewer’s visual judgement are recorded. Record homeowner acceptance, survey release, order decisions and professional construction information separately.


### Check the view from both sides

Where a doorway or glazed partition reveals another designed room, align its current furnished model to the shared opening. Compare a camera from each side. Look for the correct furniture, curtain stack on the correct jamb, visible lining and hardware, including their operating state. Use a second view when reflections, foliage or a curtain hide the detail. Record what the camera can actually resolve.

If a background changes, recheck close-ups and activity views that share it. Keep earlier issued packs intact. Link the corrected view first in the house presentation and identify any older view retained only to explain an activity. A planning gallery can show this evidence while the formal photographic issue is held.

For each visible opening, record a separate `head_review`. Set `expected` to `closed above`, `glazed overlight`, `intentional opening` or `mixed`. Inspect the head in both the camera and photograph. Record `camera_state` and `photo_state` and mark the corresponding normalised `camera` and `photo` regions around the head. Record a `finding`. If cropped or hidden, use `outside-frame` or `occluded` with its view-specific `camera_reason` or `photo_reason` and verify the assembly in the [native elevation](../../freecad-renovation/references/opening-clearances.md#check-the-doorway-in-elevation). A general statement that hardware looks continuous cannot clear a gap above a leaf.
