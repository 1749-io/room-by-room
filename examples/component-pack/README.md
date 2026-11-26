# A library review, drawing and shopping schedule

[Download the verified example house pack](reference/Alder-Cottage-handover.zip). Extract it and open `Start here.html`. Each room, drawing and shopping download retains the file issued separately.

The fictional Alder Cottage commission is a CAD-only review of a reading chair, bookcase and opening door. The shelf purchase depends on a fixing check. The worked house has one registered room. A kitchen shopping row tests whether unrelated items reach the recipient.

To inspect the editable native layout and measure the moving door against that chair, bookcase and lamp, follow the [FreeCAD library walkthrough](../furnished-room/README.md).

Install the pack dependencies and run the replay with a **new directory outside the repository**. It creates an isolated house and backup location, issues each component separately, issues the room combination and assembles a house edition from the three standalone releases. The example records automated fixture checks. A live commission needs the actual recipient-file review described in the [delivery skill](../../skills/pack-delivery/SKILL.md).

```sh
python -m pip install -r requirements/packs.txt
python examples/component-pack/replay.py "../Alder Cottage replay"
```

The last line identifies the saved `Start here.html`. In its folder open the room review, forward the drawing PDF or filter the shopping workbook. The house ZIP has the same relative tree. The two rows in the shopping schedule are the retained reading chair and two oak shelves at £84.50 each. The £169 shelf line remains on hold. The [room request](request.json) and [house request](house-request.json) show the two supported inputs.

## Use with a named house

Save the recipient request under the house. A shopping-only request needs `version`, `house`, `room`, `audience`, `purpose`, `components`, `limitation` and `next_action`. The drawing and room fields in the example apply only to their respective components.

```sh
python house.py begin-revision "Alder Cottage" OWNER-01 --pack-request owner-request.json
python house.py plan-pack "Alder Cottage" OWNER-01
python house.py build-pack "Alder Cottage" OWNER-01
python house.py check-pack "Alder Cottage" OWNER-01
```

Open the extracted files. Record the actual review with the `--reviewer` and `--finding` options, then use the normal [save and recovery workflow](../../docs/output-revisions.md). A saved issue can be verified later with `check-pack`. The private `issue-manifest.json` holds the source revisions and digests. Recipients get only the `delivery/` contents, including their readable index and file register.

## Regression checks

```sh
python -m unittest discover -s tests -p test_component_packs.py -v
```

The suite exercises the public commands, retained items, exact workbook totals, stale design and shopping evidence, omitted rooms, an incomplete workbook with valid archive hashes, repeatable builds and binary identity between the standalone and full-house downloads.
