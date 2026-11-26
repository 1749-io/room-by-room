# Worked renovation examples

For a purchasing handover across three rooms, run [Maple Mews](multi-room-shopping/README.md). It reconciles shared purchases and all six recipient files.

To issue a single room, drawing or shopping schedule, replay the [Alder Cottage component handover](component-pack/README.md). It also builds an offline house edition from the saved standalone files.

For a homeowner presentation, architect appointment pack or buyer brief, replay the [Alder Cottage audience editions](audience-packs/README.md). The example checks all three on their own and inside the full house issue.

For approved surfaces, a base and option cost comparison or a dependency-linked programme, open the [trade schedules example](trade-schedules/README.md).

For a signed-off arrangement carried across a floor plan, section and camera, replay the [visual release check](visual-release/README.md).

Choose by the homeowner's question. **Replay** means you can run the calculation or test. **Desk exercise** gives the inputs, reasoning and outcome to check by hand.

| Homeowner question | Worked example | Kind |
| --- | --- | --- |
| What happens when the engineer returns the pier footprint? | [Five kitchen layouts with four and eight diners, measured in reopened FreeCAD](whole-house-changes/README.md#1-where-the-pier-changes-the-kitchen) | Replay from native measurements |
| Where should the garden table go for afternoon sun? | [Two spots, five times and a hedge-height sensitivity](garden-sun/README.md) | Replay, standard Python |
| Can we change the garage frontage? | [Missing decision notice, parking condition and the conversion section](../skills/renovation-pack/references/uk-consents.md#worked-enquiry-with-a-missing-decision-notice) | Desk exercise with official sources |
| Will a flush patio drain away from the house? | [Two spot levels and an untraced outlet](household-decisions.md#1-will-a-flush-patio-send-rain-towards-the-kitchen) | Desk exercise |
| Could a visitor reach the shower with a walking aid? | [A straight passage, a turn and a threshold](household-decisions.md#2-will-a-visitor-manage-the-downstairs-shower) | Desk exercise with a route test |
| Can we live here while the bathrooms are changed? | [Twelve nights, a shared supply, delivery access and a delayed handover](whole-house-changes/README.md#3-which-bathroom-works-tonight) | Replay with failed and workable sequences |
| Which builder leaves enough money for the rest of the house? | [Two R3 tenders, common exclusions, reserve and the cost of staying](whole-house-changes/README.md#2-which-builder-fits-the-house-budget) | Replay with fictional offers and a cost sensitivity |
| Can I accept a substitute appliance? | [A cheaper fridge in the agreed opening](household-decisions.md#5-can-a-cheaper-replacement-fridge-go-straight-on-the-order) | Desk exercise |
| Would insulation stop the office working? | [Finished wall build-up against an occupied desk](household-decisions.md#6-will-the-retrofit-leave-enough-room-for-the-desk) | Desk exercise |
| Will the music room disturb a call upstairs? | [Two evening uses and a repeatable listening trial](household-decisions.md#7-is-the-music-room-quiet-enough-for-an-evening-call-upstairs) | Desk exercise |
| How much of the solar yield saves us money? | [On-site use, exported energy and the roof decision](household-decisions.md#8-does-a-solar-quote-save-what-the-brochure-implies) | Desk exercise |

## Structural, circulation and visual reviews

| Where to start | What the agent does | What the result permits |
| --- | --- | --- |
| [How a hinge changed a lounge layout](lounge-door.md) | Follows an occupied route through two door options, camera review and handover on a real commission. | Shows which option met the household target and what still needed checking on site. |
| [Fictional kitchen opening, two solvers](structural-opening/README.md) | Runs PyNite for a beam and FreeCAD FEM with CalculiX for two solid meshes. Checks reactions and deflection against a hand calculation, then reads stresses from the reopened native file. | Confirms that the tools work on known inputs. A live alteration still needs its own evidence and engineer's assessment. |
| [Shopping past an occupied sideboard](../tests/test_routes.py) | Measures an illustrative 850 mm shopping journey. The original throat gives about 550 mm before allowing for the sideboard in use. One permitted move still blocks collection of the shopping. A second move clears the route. | Demonstrates how to retry within a furniture-only brief and how a failed option can be useful. [How to run it](#replay-the-sideboard-example) |

## Replay the sideboard example

From the repository root, install the [optional route dependencies](../requirements-routes.txt) in the active Python environment. Then run the two existing tests.

```sh
python -m pip install -r requirements-routes.txt
python -m unittest discover -s tests -p test_routes.py -k buyer_can_review -v
python -m unittest discover -s tests -p test_routes.py -k rearrange_only_the_sideboard -v
```

A green test includes the expected restricted route and the failed first move. For a house, use that household's occupied geometry, agreed travel width and change permissions. [Route study guidance](../skills/freecad-renovation/references/route-studies.md)

## Save another worked run

Start with the question or brief, the allowed changes, and where the decision belongs in the [existing workflow](../docs/agent-workflow.md). For a reusable example, put fictional or shareable inputs and their units under `examples/`, with the command to run, optional dependencies and a small saved result. State which actions use live MCP and which calculations run locally. Give the reader an independent check, a tolerance where appropriate, and the outcome that should stop the next stage. Test the instructions in a fresh output folder.

For a real room, keep its sources, permissions and issue files under the named house. When sharing a lesson publicly, prepare an example with its own permitted inputs and check what a reader can reproduce from a fresh clone.
