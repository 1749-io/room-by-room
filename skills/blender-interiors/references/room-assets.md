# Room asset library

The [room asset library](../scripts/room_assets/__init__.py) builds furniture, fittings and garden context in Blender from code alone. The same request always gives the same geometry at the stated size. Nothing is imported or downloaded, so there is no third-party asset to license or record.

## When a library asset is enough

Every library asset is a stand-in: true to size, recognisable in outline and plain in detail.

| Situation | Use |
| --- | --- |
| Furniture exploration before a layout is chosen | A library asset at the candidate's stated size |
| A piece the homeowner has not yet selected | A library asset at the working size, described as a stand-in in the room review |
| Context beyond the room: garden, adjoining rooms, doors and blinds | A library asset at the surveyed or CAD size |
| A selected product whose distinctive form the asset matches | The asset at the listed size and finish. Record the remaining differences in the product comparison |
| Any other selected or distinctive retained piece | Model that product from its reference with [a one-off builder](#build-a-one-off-piece-for-one-house). Keep the nearest library asset out of the furnished camera |

Size alone does not make an asset product-matched. Compare its outline, proportions, legs, arms and finish with the product reference before a furnished camera relies on it.

## Build, place and read back

Run this through `execute_blender_code` in the named working copy. The library loads from disk, so use the absolute path to this skill's `scripts` directory. If the connector refuses the import, keep its settings intact and report that. Retyping a builder by hand loses the repeatable result.

```python
import sys
sys.path.insert(0, r"/path/to/skills/blender-interiors/scripts")
import room_assets

chair = room_assets.build(
    "rattan_armchair", "C01 armchair 1", size_mm=(740, 790, 820),
    collection="Furniture | conservatory",
    tags={"furnishing_room": "conservatory", "shopping_ref": "C01"})
room_assets.place(chair, centre_m=(0.55, 9.40), yaw_deg=-12)
report = room_assets.measure(chair)
```

- **Size.** Millimetres, in the order each catalogue entry states. The scene must use metres with a unit scale of 1.0.
- **Origin and front.** The root is an empty at the centre of the footprint on the floor, and the natural front faces the asset's +Y. A hanging fitting's root sits on the floor directly below it. A tree's root is the foot of its trunk.
- **Placement.** `place` takes a plan position in scene metres and a yaw, anticlockwise from +Y seen from above. Take both from the reviewed CAD placement.
- **Tags.** Put `furnishing_room` and `shopping_ref` on one representative per purchasing unit, as [the quantity check](../scripts/furnishing_readback.py) expects. The root also records the asset, size, options and finishes that made it.
- **Parts.** Each mesh is named `<name> | <part>`. Seating has separate `seat` and `back` meshes for the [layout read-back helper](../scripts/layout_readback.py).
- **Finishes.** Pass `finishes={"frame": "oak"}` with a palette key from [parts.py](../scripts/room_assets/parts.py) or the name of a material already in the file. A material that already exists under the palette's name is reused unchanged.
- **Read-back.** `build` measures the evaluated meshes and removes an asset more than 1 mm from the request. `measure` returns the requested and measured extents and the world bounds after placement. Save that report with the scene evidence and compare the world bounds with CAD.
- **Removal.** `room_assets.remove(root)` deletes the asset and its parts. Each instance needs its own name.

## Catalogue

[catalogue.json](../scripts/room_assets/catalogue.json) is the index. It gives each asset's summary, the meaning of its three sizes, its origin, default, smallest and largest sizes, options and default finishes. A request outside those limits is refused with the permitted range.

| Asset | Stands in for | Default size, mm | Options |
| --- | --- | --- | --- |
| `rattan_armchair` | Rattan tub armchair with a cane shell and loose cushions | 740 × 790 × 820 | `seat_height_mm`, `arm_height_mm` |
| `block_armchair` | Upholstered armchair as softened blocks | 750 × 780 × 850 | `seat_height_mm`, `arm_height_mm` |
| `dining_chair` | Timber side chair with a padded seat | 450 × 450 × 900 | `seat_height_mm` |
| `dining_table` | Rectangular table on four legs | 900 × 1,600 × 750 | `top_thickness_mm`, `leg_mm`, `leg_inset_mm` |
| `sideboard` | Long low cabinet on sledge legs | 1,600 × 450 × 850 | `leg_height_mm` |
| `side_table` | Round occasional table | 400 × 400 × 500 | `top_thickness_mm` |
| `pendant` | Drum pendant on a flex, with an optional light | 320 × 320 × 200 shade | `underside_mm`, `ceiling_mm`, `light_watts` |
| `roller_blind` | Blind cassette with the fabric lowered by a stated drop | 1,500 × 60 × 80 cassette | `head_mm`, `drop_mm` |
| `glazed_leaf` | One glazed door leaf, hinged or sliding | 900 × 44 × 2,040 | `stile_mm`, `bottom_rail_mm` |
| `tree` | Tree at a surveyed height, for context through glazing | 5,600 × 4,800 × 9,000 | none |
| `hedge` | Clipped hedge | 3,000 × 700 × 1,900 | none |

The garden assets show height and mass for a view or a shadow discussion. They are not a planting design.

## Choose an example to start from

Read the nearest builder before writing a new one, then keep its structure and change its dimensions.

| Form to build | Start from | What to copy |
| --- | --- | --- |
| Straight timber: benches, stools, desks, shelving, cabinets | [dining_chair](../scripts/room_assets/seating.py), [dining_table, sideboard](../scripts/room_assets/tables.py) | `box` parts with a 4 mm bevel, legs set in from the corners, the top measured down from the overall height |
| Upholstery: sofas, ottomans, beds, headboards | [block_armchair](../scripts/room_assets/seating.py) | `box` parts with a 15 to 30 mm bevel, a base raised on feet, arms as a share of the width, a loose cushion as its own part |
| Bent rod, cane, wire or tube frames | [rattan_armchair](../scripts/room_assets/seating.py) | Centre lines sent to `tubes`, a plan curve reused at several heights, `rod_to_floor` for a raked leg |
| Loose cushions, rugs, mattresses and shaped tops | The seat in [rattan_armchair](../scripts/room_assets/seating.py) | `slab` from a plan outline listed anticlockwise, with a 30 mm bevel for a soft edge |
| Round or turned pieces: pedestal tables, lamps, planters | [side_table](../scripts/room_assets/tables.py) | `cylinder` parts stacked on one axis, with a multiple of four segments |
| Hung or wall-fixed pieces: lights, blinds, shelves, mirrors, pictures | [pendant, roller_blind](../scripts/room_assets/fittings.py) | The root on the floor below, heights passed as options, the occupied extent returned |
| Framed and glazed pieces: doors, windows, screens | [glazed_leaf](../scripts/room_assets/fittings.py) | Stiles and rails as `box` parts round a thin pane in the glass finish |
| Planting: trees, shrubs, pot plants | [tree, hedge](../scripts/room_assets/garden.py) | `ellipsoid` masses laid out in units, then scaled to the requested spread |

Work the overall size back from the request, as each example does:

- A `box` bevel and a `slab` bevel round the edges inwards. The stated size is the outside.
- A rod occupies its centre line plus its radius on every side. Set a hoop's centre line one radius inside the overall width, depth and height.
- A part with its own rotation, such as a leaning back cushion, is measured where it ends up. Keep it inside parts whose position is exact.
- Name the sitting surface "seat" and the backrest "back" so the layout read-back can find them.
- Give repeated parts numbered names, and derive every position from the arguments.

## Build a one-off piece for one house

A product that only one house needs stays in that house's revision. Write its builder there in the same form, send the definition through MCP with the call, and use `build_custom` so it gets the same record, tags and size read-back as a catalogue asset. It has no catalogue limits and no default finishes.

```python
from room_assets import build_custom, measure, parts, place

def hall_bench(root, size, finishes, slats):
    """Slatted oak bench on two plank ends."""
    width, depth, height = size
    gap = 0.012
    slat = (depth - gap * (slats - 1)) / slats
    for index in range(slats):
        y = -depth / 2 + index * (slat + gap)
        parts.box(root, f"slat {index + 1}", -width / 2, y, height - 0.03, width / 2, y + slat, height, finishes["timber"], bevel=0.003)
    for index, x in enumerate((-width / 2 + 0.08, width / 2 - 0.12)):
        parts.box(root, f"end {index + 1}", x, -depth / 2, 0, x + 0.04, depth / 2, height - 0.03, finishes["timber"])

bench = build_custom(hall_bench, "H01 hall bench", (1200, 380, 450), collection="Furniture | hall",
                     finishes={"timber": "oak"}, tags={"furnishing_room": "hall", "shopping_ref": "H01"}, slats=4)
place(bench, centre_m=(4.9, 1.2), yaw_deg=90)
report = measure(bench)
```

Save the builder's source and the `measure` report with the revision. Compare the saved view with the product reference, since the read-back confirms size and not likeness. Move a one-off into the catalogue once a second house needs it.

## Add an asset

Add a builder to the catalogue when a house needs a form it lacks and the piece is likely to recur.

1. Write one function in the matching module under [room_assets](../scripts/room_assets/seating.py), named as the asset. It receives the root, the size in metres, the finishes and its options, and adds parts with the helpers in `parts.py`. Derive every dimension from the arguments. Use no random values, files or network.
2. Keep the result inside the requested size. Return the occupied extent only when it differs from a box centred on the root.
3. Add the entry to `catalogue.json` with tested size limits, and a row to the table above.
4. Run the check below and inspect the saved picture beside a reference for the form.

```sh
blender --background --factory-startup --python skills/blender-interiors/scripts/check_room_assets.py -- report.json --views views
```

The [check](../scripts/check_room_assets.py) builds every asset at its default, smallest and largest sizes, turns it on the floor, measures it again and builds it twice to confirm the geometry repeats. It also sends a one-off builder through `build_custom` and confirms that a wrongly sized one is refused. `python -m unittest discover -s tests -p test_room_assets.py -v` runs the same check when Blender is installed, and checks the catalogue against the builders and this page either way. Mesh generation can differ between Blender releases, so the report records the version that produced it.
