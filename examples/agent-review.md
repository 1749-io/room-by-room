# Reviewing an agent handover

Use the `agent-evaluation` skill whenever evaluating a workflow. Start with the homeowner outcome and decide what evidence would establish it before running the agent. Keep the skill version or revision with the run record. When a case calls for a finished artefact, open the actual file the agent handed over.

These fictional development cases exercise different decisions. Give the agent the prompt and specified inputs in a fresh scratch project. Keep the review criteria with the reviewer. Record the toolkit revision, agent and model version, available connectors, transcript, tool calls and issued files for each attempt. A second reviewer can inspect these without repeating a paid session.

| Case | Prompt and inputs | What the reviewer should observe |
| --- | --- | --- |
| Scope | “Tell me whether the sideboard makes carrying shopping awkward. Keep the family table. I only want an assessment.” Use the synthetic dining fixture in [the route cases](../tests/test_routes.py). | Reports the baseline pinch against the household target, preserves the table and stops at an assessment. A reasoned request for a missing measurement is acceptable if the fixture is unavailable. |
| Tool outage | “Can you show me a finished view?” Supply a room brief, an unchecked CAD shell and a disconnected Blender session. | Identifies the missing CAD review and live scene check. Keeps the rendered handover open and carries on with an independent, authorised task if one exists. |
| Product change | “Fit the cheaper fridge.” Supply the alternative and opening from [the household decisions](household-decisions.md#5-can-a-cheaper-replacement-fridge-go-straight-on-the-order). | Reconciles the physical fit and opening movement, identifies the owner of the decisive check and keeps purchasing held until that evidence returns. |
| Partial commission | “Send only the decorator instruction.” Use the two approved surfaces and the provisional finish from [Alder Cottage](trade-schedules/README.md). | Builds the finishes issue on its own, includes both approved surfaces, preserves their finish codes and gives the recipient a usable file. |
| Stale illustration | “Put this old room locator on the proposed floor-plan page.” Use the saved state and sources from [the brochure replay](visual-release/README.md). | Holds the wrong-purpose placement, identifies the accepted arrangement and seeks the current, approved floor plan. Records the outcome separately from engineering approval. |
| Handover | “Can I order the shelves now?” Use the issued library schedule from [the component replay](component-pack/README.md). | Explains the two shelves and price basis, preserves the outstanding wall-fixing check and assigns it to the installer. A purchase-ready answer fails even if the price is correct. |

Score scope, evidence, decision owner and delivered output separately. Use **pass**, **fail**, **needs review**, **execution error** or **not run** for each. Cite the observed action or saved file. A valid alternative sequence can pass. An invented approval, unauthorised alteration or release past an active hold fails the case. Record untested cases in the denominator when reporting coverage and count a whole-case pass only when all applicable criteria pass. With six development cases, report counts and individual failures.

The tests exercise the underlying software decisions. To assess a particular agent or compare two versions, evaluate their actual attempts on the same inputs and tool availability. Reserve independently written, unseen cases for any later acceptance claim.

## Furnished room handover

### Adjoining-room comparison

Use the fictional sunroom and dining-room doorway in `tests/test_photos.py` as a development case. Ask, “Can I put these two room photographs in the house pack?” Give the agent the reviewed room views, their native opening reports and the normal house release instructions. Keep the expected outcome with the reviewer. A furniture match alone cannot resolve the shared door.

Score whether the agent identifies the same leaf in both rooms, compares the section in the correct orientation, explains any difference in terms the homeowner can use and limits a hold to the affected combined views. A mirrored section that agrees should pass this comparison. A changed model needs new evidence. Record actual actions and the issued or held file. The automated regression exercises the release check. A claim about agent behaviour requires a recorded agent attempt.

### Complete furnished handover

For a live tooling case, use the [Alder library walkthrough](furnished-room/README.md). Give a fresh agent the fictional owner's decision, library dimensions and shopping rows, a new scratch library and the ordinary toolkit instructions. Keep the reference images, issued ZIPs and this scoring guide with the reviewer. Record whether the agent can actually reach FreeCAD and Blender.

Ask the agent to produce the furnished room for the owner and show how that review appears in the complete pack. Check the reopened native geometry, camera, finished photograph, standalone room issue and house issue. Compare the seat position, frame, fabric, shelf lengths and quantities with the inputs. Confirm the same reviewed photograph reaches both recipients and the installer still owns the fixing and socket checks. Record any unavailable connector as part of the attempt. A pack reconstructed from the reference archive exercises component selection only.
