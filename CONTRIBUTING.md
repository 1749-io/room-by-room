# Working on the renovation toolkit

## Try a release

Use Python 3.11 or 3.12 and Git. In a new virtual environment, run the following from the repository root. On Windows activate the environment with `.venv\Scripts\Activate.ps1`. On macOS or Linux use `source .venv/bin/activate`.

```sh
python -m venv .venv
# Activate .venv before the next command
python -m pip install -r requirements-dev.txt
python examples/trade-schedules/replay.py "../Alder demo"
```

Use a new output directory for each replay. Open the printed `Start here.html`. The house issue contains a room review, drawing, shopping workbook, three audience editions and three trade schedules. Each can be forwarded separately. The example uses fictional decisions and geometry. For a first run with standard Python only, try `python examples/whole-house-changes/replay.py quotes`.

## Where changes belong

| Location | Responsibility |
| --- | --- |
| [house.py](house.py) and the root `house_*.py` modules | Create a project, resolve its records, check a handover, save a revision and recover private backups. Start with `python house.py --help`. |
| [AGENTS.md](AGENTS.md) and [skills](skills/) | Project instructions and the five task-specific skills. The agent interprets the brief, inspects evidence and records decisions. |
| [templates](templates/) | The house dashboard, brief, room files and registers created by the CLI. Keep existing houses readable when adding a field. |
| [tools](tools/) | Render, assemble and verify recipient files. Native scene and drawing helpers sit beside the skill that runs them. |
| [examples](examples/README.md) | Fictional inputs, expected outcomes, executable replays and worked decisions. Each replay names its tool requirements. |
| [docs](docs/agent-workflow.md) | Workflow maps, evidence requirements and tool setup. Diagram source and renderer sit beside the generated SVGs. |
| [tests](tests/) | Regression and release checks. Browser exercises open the actual files offline and follow the recipient's links. |

## Route a request

| When the homeowner asks for | Start here | Evidence for the handover |
| --- | --- | --- |
| A change, trade-off or survey decision | [Renovation pack](skills/renovation-pack/SKILL.md) | Brief, permissions, responsible decision-maker and next evidence |
| A measured alteration or occupied layout | [FreeCAD renovation](skills/freecad-renovation/SKILL.md) | Reopened native geometry, checked plan and section where required |
| Furniture options or a furnished camera | [Blender interiors](skills/blender-interiors/SKILL.md) | Permitted study returned to CAD, or product-matched camera and scene read-back |
| A schedule, drawing, room, audience edition or house ZIP | [Pack delivery](skills/pack-delivery/SKILL.md) | Frozen commission, checked standalone files and a reader receipt |
| Existing and proposed property brochures | [Property comparison](skills/property-comparison-pack/SKILL.md) | Signed visual placements across the two tours and printed pages |

## Verify a contribution

```sh
python -m unittest discover -s tests -v
python -m playwright install chromium
python tests/browser/comparison_pack.py
python tests/browser/component_pack.py
python tests/browser/audience_packs.py
python tests/browser/trade_schedules.py
```

For changes to a workbook or editable deck, also run the matching browser script with `--office /path/to/soffice` to recalculate or render the edited file in LibreOffice. For a diagram change, run `python docs/render_workflow.py` with Graphviz installed. For native geometry or camera changes, follow the [tool readiness checks](docs/tools.md) on a scratch document and inspect the saved result.

Use a fictional example for a regression. Show the input, deciding observation and recipient file. Keep household sources, quotes, camera exports and revision archives in private storage. For changes to agent instructions, review the [behaviour cases](examples/agent-review.md) alongside the applicable software tests.

## Preparing a public revision

Start from the public toolkit's own history. Bring separately reviewed source changes into this checkout. Keep private project history, branches, issue exports, local agent folders and household backups in their owning storage.

Stage the intended changes, then run `python tools/check_docs.py` and `python tools/check_public_tree.py --history`. The second command checks all reachable commits for private paths, reads the Git index and checks binary content against [the asset inventory](examples/asset-inventory.json). For a new binary, inspect its contents, metadata, origin and redistribution terms, then record its path and SHA-256. For a pack, also reproduce it from its fictional inputs, open its nested Office files and compare its recipient files. Keep the licence notices with the work. [Dependency and asset terms](THIRD-PARTY.md)

Test a fresh clone in a path containing spaces. Run the suite and offline reader checks there. Scan the candidate's Git history and the clean tree, including nested archives, with the pinned scanner in [the privacy workflow](.github/workflows/checks.yml). Track local review evidence privately. At first publication apply the [main ruleset](.github/rulesets/main.json) and verify that the required check names match the jobs that actually ran. Enable the destination's available secret scanning, push protection and private reporting and check their settings there.
