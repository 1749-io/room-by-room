# Replaying a signed design decision

A fictional homeowner has accepted a 900 mm opening in the south wall and excluded the fixing detail. The example saves editable native parameters and their drawing generator, the actual fictional decision, its acceptance binding, a floor plan, a section and a schematic camera image. Its reviewer records what each derivative shows and where it may be used.

```sh
python -m pip install -r requirements-packs.txt Pillow playwright
python -m playwright install chromium
python examples/visual-release/replay.py "../Visual release example"
```

Open `houses/example-house/revisions/BROCHURE-01/outputs/Brochure/Start here.html` in the new directory. The proposed brochure contains the retained opening in the plan, section and camera mock. The adjacent `Visual-uses.json` lists all placements. In `houses/example-house/`, open `design-states.json` to read the arrangement independently of its illustrations and `visual-approvals.json` to inspect the grant for each use. The geometry and sources belong to the fictional example. The schematic camera image exercises the release workflow.

From the repository root, run the following against the generated example.

```sh
python house.py --houses-dir "../Visual release example/houses" check-design "Example House" proposed-arrangement --scope floor/ground
python house.py --houses-dir "../Visual release example/houses" check-visual "Example House" proposed-plan --phase proposed --purpose comparison.layouts --scope floor/ground --view plan
python -m unittest discover -s tests -p test_visual_release.py -v
```

Changing the manifest's proposed floor plan to an existing room locator, omitting the required section, changing the accepted geometry or hiding a visible feature all put the issue on hold. The [release guide](../../docs/visual-release.md) describes the records and correction process.
