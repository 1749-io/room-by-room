# Alder Cottage audience editions

A fictional homeowner is deciding whether to add two oak shelves to the library. The homeowner needs to see how the room works, the architect needs the existing drawing and survey return, and a buyer wants to know what to check at a viewing. A shelf fixing and socket check is outstanding. The three editions use the same checked plan and distinguish the priced goods from unpriced work.

[Download the worked house issue with all three editions](reference/Alder-Cottage-audience-editions.zip). Extract it and open `Start here.html`.

| Edition | What the recipient can open | What to check |
| --- | --- | --- |
| Homeowner presentation | Editable PowerPoint and companion 16:9 PDF | Open the reviewed plan, options, cost basis and next decision. Select and edit a text box in the deck. |
| Architect pack | Brief and drawing set in one PDF, individual forwardable PDFs, drawing register CSV | Check the appointment scope, survey and fee assumptions. Follow the register's relative file path and compare the separate sheet with its bound copy. |
| Buyer brief | Printable A4 PDF | Check the source date, assumptions and inclusions. Take the viewing questions and professional enquiries to the appointment. |
| Full house | Offline start page, transmittal, room review, drawing and shopping schedule, plus all commissioned audience editions | Open each edition under `Briefs/`. Its own entry page and every downloadable document are identical to the standalone issue. |

## Replay

Run from the repository root with Python 3.11 or newer. Choose a new directory outside any live house. The replay creates its own house, draft revisions and verified backups there.

```sh
python -m pip install -r requirements/packs.txt
python examples/audience-packs/replay.py "../Alder reader example"
```

Open `houses/alder-cottage/revisions/HOUSE-ALL/outputs/pack/delivery/Start here.html` under that directory. The `OWNER`, `ARCH` and `BUYER` revision folders each contain their own ZIP. Extract an edition before using its entry page. A recipient can also take the individual PowerPoint or PDF. Keep the architect register with its adjacent `Drawings/` folder when forwarding the whole drawing set.

## Commission a single edition

The [replay](replay.py) writes a complete `request-OWNER.json`, `request-ARCH.json`, `request-BUYER.json` and `request-HOUSE-ALL.json` into the fictional house. Adapt the relevant request and its [homeowner](homeowner.json), [architect](architect.json) or [buyer](buyer.json) copy file. For example, a standalone architect request looks like this.

```json
{
  "version": 1,
  "profile": "edition",
  "house": "alder-cottage",
  "components": ["architect-pack"],
  "audience": "Architect",
  "share_with": ["Homeowner"],
  "purpose": "Agree the scope of a library storage appointment.",
  "limitation": "Existing library sheet only. Wall construction and services require a survey.",
  "next_action": "The architect agrees a measured survey return with the installer.",
  "rooms": {"library": {"drawing": "DRAWING"}},
  "editorial": "architect.json"
}
```

Use the named house and its actual saved source issues. Every registered room needs an entry. A room with several commissioned sheets can name an ordered list of drawing revisions. Homeowner room reviews also accept a list for existing and proposed comparisons. Declare a genuinely unavailable or expressly excluded source in `omissions`, with the room, source role and a reader-facing reason. For example, `"omissions": {"library": {"shopping": "Buyer to obtain prices after the viewing."}}` works alongside `"rooms": {"library": {"drawing": "DRAWING"}}` in a buyer request. The reason prints in the issue. The architect pack requires at least one issued drawing.

The editable copy contains named chapters with `label`, `text` and a publishable `basis` for each entry. Attach relevant local source files using `evidence`, for example the approved budget or survey return. The builder freezes and rechecks their contents. Only the approved words enter the recipient files. Use these fields to describe any applicable fees, contingencies, exclusions, purchase assumptions and time to occupation. The shopping subtotal is calculated from allocated, priced lines in the saved schedule. Shared allocations and missing prices are identified separately.

Run the usual `begin-revision --pack-request`, `plan-pack`, `build-pack`, `check-pack` and `save-revision` sequence. Open the extracted issue and record what the recipient can do with the actual files. To include saved editions in a house commission, add `"editions": {"homeowner-presentation": "OWNER", "architect-pack": "ARCH", "buyer-brief": "BUYER"}` to its [house request](../component-pack/house-request.json). The house build checks permissions at both the room source and edition level and copies the reviewed publications.

## Reproduce the reader checks

```sh
python -m unittest discover -s tests -p test_audience_packs.py -v
python -m pip install playwright
python -m playwright install chromium
python tests/browser/audience_packs.py --house "../Alder reader example/houses/alder-cottage"
```

The browser exercise navigates all four extracted ZIPs offline at phone and desktop widths and downloads each audience file from both entry points. Add `--office /path/to/soffice` to render the editable PowerPoint independently and check slide text, pictures and page bounds. The production command builds the companion PDF directly from the same approved slide layout.
