# Alder Cottage library

The fictional owner wants to reach the bookcase while someone reads beside the south window. The accepted layout retains one oak chair in sage linen and provides two 875 mm oiled oak shelves. The installer still needs to confirm shelf fixings and the socket location. [Decision and editable dimensions](library.json)

## Replay the layout check

Open the FreeCAD Python console and run the following, substituting the location of your clone and a new output folder. The script creates a separate document, saves an editable model, reopens it, and measures the door movement against the chair, bookcase and lamp.

```python
from pathlib import Path
import runpy

example = Path("/path/to/house-renovations/examples/furnished-room")
build = runpy.run_path(str(example / "build_cad.py"))["build"]
print(build(Path.home() / "Alder library replay"))
```

Open `Alder library.FCStd` to inspect the model. Turn on **Conservative hall door swing** in the model tree to see the tested area. `Layout checks.json` records the distances measured after reopening the model.

| Check | Reference result |
| --- | ---: |
| Full door swing to retained chair | 1,769.619 mm |
| Full door swing to bookcase | 1,594.936 mm |
| Full door swing to lamp | 2,564.949 mm |
| Open leaf to head | 6 mm |
| Selected shelf lengths | 875 mm each, two shelves |

The chair, bookcase and lamp use bounding shapes for this clearance study. To try a change, edit a copy of `library.json` beside the script and build into a second folder. Reducing the distance to zero holds the check.

## Open the existing handover

The same room dimensions and selections appear in the [standalone room, drawing and shopping editions](../component-pack/README.md). The [complete worked house ZIP](../trade-schedules/reference/Alder-Cottage-trade-handover.zip) also includes the homeowner presentation, architect pack, buyer brief, decorator finishes, editable costs and programme. Extract it and open `Start here.html`.

That downloadable issue uses a CAD-only room review. The furnished camera, final concept photo and their purpose-specific approvals are the remaining stages for the illustrated room walkthrough.
