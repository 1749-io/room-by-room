# Alder Cottage trade schedules

The fictional library has two approved paint samples and an optional pair of oak shelves. The decorator needs an instruction to take on site, the homeowner wants to compare costs, and the installer needs a sequence that honours the fixing check. Each recipient can take a single workbook, a portable CSV or a small ZIP with its own offline, printable reader.

[Download the complete worked house issue](reference/Alder-Cottage-trade-handover.zip). Extract it and open `Start here.html`. The three schedules sit under `Schedules/` alongside the shopping files. The room review, drawing, homeowner presentation, architect pack and buyer brief are also included.

| Schedule | Commission and source | What to open or change |
| --- | --- | --- |
| Decorator finishes | Named surfaces and revision in each room's `decorator-finishes.csv`, with the actual sample approval or explicit instruction | Check the manufacturer, colour, code, sheen and sample reference. Print the offline page for site. The provisional bookcase finish stays outside the issued rows. |
| Cost schedule | Selected scopes in the house's `budget.csv` with a base, named option or excluded classification | Open **Cost summary**, then edit low and high amounts on **Cost lines**. The base allowance is £210 to £300. Adding shelves brings priced goods and works to £379 to £469, with fitting and delivery still unpriced. |
| Programme | Selected activities in the house's `programme.csv`, their dependencies and the forecast start | Change the start date, durations or date constraints. Increasing the fixing check from one day to four moves the optional fitting from 18 to 21 January 2027 and flags the late shelf decision. |

## Replay the example

```sh
python -m pip install -r requirements-packs.txt
python examples/trade-schedules/replay.py "../Alder trade example"
```

Use a new directory outside any live house. The replay creates its own private Alder Cottage house and backups. Each issued revision has its own ZIP under `revisions/<issue>/outputs/pack/`. The standalone revisions are `FINISH`, `COST` and `PROG`. The combined issue is `HOUSE-TRADE`.

## Commission a single schedule

Select the relevant entry from [the example requests](requests.json). Add `"version": 1`, `"profile": "schedule"` and the named house's `"house"` ID. Save that single object as a JSON file in the house and use it with `begin-revision --pack-request`. Run `plan-pack`, `build-pack` and `check-pack`. Open the extracted issue, test the workbook and record the reviewer and finding before `save-revision`. A standalone schedule reads its own sources. A full house request adds the saved issue IDs to its `editions` object.

**Finishes.** The [sample register](finishes.csv) uses the existing decorator fields and an optional public `decision_ref`. The latest recorded row for a surface governs issue. Append a replacement decision under its new revision. Each selected surface must pass `check-decorator` for the named revision and have readable approval evidence. The private evidence file stays in the house.

**Costs.** The [budget example](budget.csv) retains the standard budget fields. Optional columns add room, trade, phase, cost type, VAT basis and space-separated shopping IDs. Linked IDs reconcile to the current quantities and priced room allocation. A given shopping ID can contribute once. Use separate scope lines for allowances, quotes, fees, contingency and exclusions as applicable. A budget scope supplies its entire low/high amount. A one-sided price stays visible on its line with a range check. Only complete ranges enter the known subtotals. Leave both amounts blank for an unpriced line. Zero denotes a known zero. Each named option adds to Base independently. Excluded lines stay visible and outside the totals. Use the declared scenario names in the workbook. Issue a new commission when the work breakdown or option set changes.

**Programme.** For an existing house, copy the [programme template](../../templates/house/programme.csv) to its root. Enter one stable task ID per activity, space-separated predecessors and whole calendar days. The first permitted start is the later of the project start, the task constraint and the day after every predecessor finishes. A zero-day milestone takes place on its start date. A blank duration leaves its finish and dependent dates open. Decision deadlines compare with the forecast finish. The workbook exposes predecessor slots in dependency order. Keep that order when changing dependencies and use an earlier task ID. Register additional tasks or dependency slots in a fresh issue. A forecast date can accompany a survey or purchase hold.

## Repeat the checks

```sh
python -m unittest discover -s tests -p test_trade_schedules.py -v
python -m pip install playwright
python -m playwright install chromium
python tests/browser/trade_schedules.py --house "../Alder trade example/houses/alder-cottage" --office soffice
```

The browser exercise opens the four extracted issues offline at phone and desktop widths, downloads each XLSX and CSV from both entry points, and prints their reader pages. With LibreOffice installed it also recalculates edited copies, including a cost option with an outstanding price and a delayed or unknown predecessor.
