# {{house}}

## Start here

Read `python house.py history "{{house}}"` with the current reviews. Use `begin-revision` before creating outputs and `save-revision` when they are ready to hand over. Each save verifies a private whole-house backup and prints its location. [Revision and recovery guide](../../docs/output-revisions.md)

Use the [house project guide](../../README.md#what-to-send) for examples of a first brief, useful property sources and what your agent can research for you.

1. Put the original email, PDF or notes in `source/original-brief/`. Keep the file as received. A brief supplied to the starter is already there.
2. Open the [working brief](brief.md). Tell us what a normal day looks like, what you want to change, what stays and how much disruption you can live with.
3. Add the rooms from your floor plan, including circulation and utility spaces. Give each one its own priorities and track shared furniture once.
4. Follow the [design workflow and diagram](../../docs/agent-workflow.md) for building, furniture studies and handover.
5. At each review, ask to see the plan, the actual scheduled items and the decision you need to make. Record your answer in [decisions](decisions.md).

| Project material | Where it lives |
| --- | --- |
| Plans, survey, listing photos, original instructions | `source/` and the [source register](sources.csv) |
| Room designs and evidence of review | Each room's README, layout-checks.csv and review.csv |
| Items to keep, buy, quote or omit | [Shopping schedule](shopping.csv) |
| Cost allowances, quotes and exclusions | [Budget](budget.csv) |
| Existing and proposed CAD, furnished Blender scenes | `models/` |
| Camera renders, product comparisons and final AI images | `views/` |
| Buyer, homeowner and architect editions | `handover/<issue>/` |

Run `python house.py status "{{house}}"` from the repository folder to see the earliest outstanding review in each room.

For a whole-house project, keep the owner's first unresolved decision here. Link the evidence they can open and name the work that can continue while that decision is open. Use one row per shared decision in the [whole-house guide](../../skills/renovation-pack/references/whole-house.md#assemble-the-house-on-one-page) when a change affects several rooms, the budget or the order of work.
