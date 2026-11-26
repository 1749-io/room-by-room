---
name: property-comparison-pack
description: Produce complete existing-house and proposed-house brochures, printable floor layouts and a guided browser tour from a listing and reviewed renovation evidence.
---

# Property comparison pack

Begin a house revision. Inventory the rooms on the existing floor plan independently of the proposed room register. Splits, conversions and additions can change the count. Record porch, parking, site access and garden where relevant.

The agent authors the two descriptions, verifies address and sources, matches rooms to photographs, and selects a walking order. Reuse the property's pre-pricing valuation description. Attribute the old listing summary and distinguish it from a verbatim extract. Label unassigned photographs, proposed views, measurement assumptions and outstanding survey items. Use a labelled floor-plan detail when a reliable before photograph is unavailable. For the proposed edition add genuine checked views of movement, equipment operation, shade or lighting. Describe a sequence of stills as a guided photo tour.

Fill a JSON manifest following [the input example](example.json). Supply each edition's complete expected room IDs from its source register, a route consisting of those rooms, floor layouts, a cover, particulars and sources. Put source images under the specified asset root and provide descriptive captions. Floor layout drawings need their own key and orientation. All image paths are relative to the asset root.

Run `python scripts/build.py MANIFEST ASSET_ROOT NEW_OUTPUT_DIRECTORY` with Pillow, PyMuPDF, Playwright and Chromium installed. Use `--channel chrome` for a local Chrome installation. The builder validates coverage, creates two standalone illustrated HTML editions and matching PDFs, and connects proposed tour stops with previous and next links. A combined PDF contains both complete editions. Reopen the output at reading size, compare the routes against the plans, test browser links, then save the house revision and link its index from the dashboard.

Use the current room photo checks before selecting images. For assets staged outside the library, pass `--house HOUSE_DIRECTORY` to load its reported-photo register and block reuse of rejected images.

Identify the house in the manifest and give every image its approved `visual_id`. For a study image, give the page its actual scope and the image its representation, for example `section`. Layout pages request `floor/<page-id>` and room pages request `room/<room-id>`. The proposed publication checks the homeowner's accepted arrangement, native geometry and consequential feature inventory. Inspect the resulting visual-use register across both browser editions and all three PDFs. See the [release guide](../../docs/visual-release.md) and [replay](../../examples/visual-release/README.md).
