---
name: renovation-pack
description: Plan and review home renovations, from a single homeowner question to checked CAD, furnished views and handover. Route questions about opening walls, daily access, sun, comfort, finishes, cost or living through works to the relevant study.
---

# Renovation pack

For a commissioned room review, individual printable drawing, room shopping schedule or an offline house edition assembled from these components, follow the [pack delivery skill](../pack-delivery/SKILL.md).

Start and resume with the house’s `CHECKLIST.md`. After a room review or survey return, run `python house.py checklist "House"`. Link the returned evidence, repeat each affected check and record the homeowner’s acceptance separately.

After the furnished camera passes, finish the agreed room photo and downloadable pack before offering another room. Follow the [furnished handover check](references/handover-gates.md#finishing-a-furnished-room) for purchase-only survey holds, an explicit pause or a views-only commission.

Give every homeowner diagram a small, sheet-specific key. Name each relevant symbol or route in plain language and inspect the final export at reading size. [Drawing keys](references/handover-gates.md#drawing-keys)

Use `house.py ask` in an open revision or the equivalent question fields on `save-revision`. Deliver its checked prompt. Show the homeowner the choice they are being asked to make. Embed the checked, labelled image in the conversation alongside a spatial or visual question. Name the same options in the image and the question, and include a short description. Save the image with the question so the next agent can show it again. [Visual questions](references/homeowner-decisions.md#show-the-choice)

On resuming, read `house.py next "House"` alongside the brief. At handover, [choose the question from the homeowner's aim and the current findings](references/homeowner-decisions.md#at-the-end-of-a-commission). Invite their reaction to work they asked to see, with relevant examples and room to move on. Ask directly when a choice blocks the work. Carry forward instructions already given. Save the full prompt with `--ask` and their reply with `house.py answer`.

Read the house's `history` on resuming. Use `house.py begin-revision` before producing outputs. Point the native app or generator at the working directory, then `save-revision` with the change, reason, author, effects and next action. The save prints the verified private backup location. Link the saved files to the review. [Commands and recovery](../../docs/output-revisions.md)

Open the named house's dashboard, original brief, working brief and dated decisions. Use the repository copy of the workflow. Follow the commissioned scope and the household's [change permissions and decision stops](references/homeowner-decisions.md). Record the current room or house revision and reopen affected work when a decision changes. Keep private sources, native models and issued packs in the named house.

Start the [glazed-room review](references/glazed-rooms.md) as soon as a highly glazed room is taken up, including on a simple request to move to that room. Return the seasonal design and furnishings to the occupied CAD review.

At every new request, change or returned finding, identify any specialist question explicit in the wording or implied by its effect. Consult the [request-to-study guide](references/specialist-design-tools.md#requests-that-trigger-a-specialist-study). Run the relevant checks within the homeowner’s permissions and return the evidence to the decision that triggered them. A combined request can need several studies. If evidence is insufficient, name the missing input, its owner and the work it holds.

| Decision in front of you | Work to do |
| --- | --- |
| What would unblock this house? | For a whole-house commission, map all affected levels, service spaces, circulation, external work and shared activities. Group interdependent decisions by work package. Record the limiting unknown, owner, affected rooms, spend and next deliverable. Use the [whole-house guide](references/whole-house.md). |
| Can this alteration proceed to design or pricing? | Follow the [UK consent enquiry](references/uk-consents.md) for the relevant nation and intervention. A new, widened or relocated opening or wall removal triggers the [structural opening review](references/specialist-design-tools.md#structural-openings). For sun, services, roof, views or phasing, choose the [study that answers the question](references/specialist-design-tools.md). |
| Does the room work? | Use the FreeCAD skill over live MCP. Preserve existing fabric, compare it with observed sources and develop permitted proposals in separate revisions. Return authorised unrendered furniture studies from Blender to FreeCAD. At proposed CAD inspect one [occupied whole-room plan](references/layout-review.md#whole-room-plan) with use, routes, fronts, shared positions and any seated views. Report material pinches in assessments. Recheck adjoining rooms when proposing changes. |
| Can we furnish or issue a photo? | Inspect the recorded evidence and run the relevant house checks. An explicit visual hold governs the output. The Blender skill owns the saved scene and transfer checks. Dress the entire selected room. Reconcile every selected or reused item's ID, variant, quantity, native object and camera visibility. Record lighting and the [whole-room colour review](references/colour-decisions.md). Generate each final AI photo from its reviewed furnished camera and compare the pair against the product references. |
| What can the recipient rely on? | Apply the [handover checks](references/handover-gates.md) and [deliverables by audience](references/deliverables.md). Reopen native files, inspect exported sheets and verify the issued archive. Give the homeowner the presentation and architect download for the agreed scope. Identify measurements, professional work, purchase holds and the next decision. |

For each room, keep the use, retained pieces, services, storage, materials, lighting, product IDs and unresolved fit in its brief. Record evidence, reviewer, finding and revision for each applicable handover. A buyer's assessment can end with a site question. A CAD-only brief stays in FreeCAD. A render hold pauses renders, final images and their publication. Use an early styling study only within the agreed scope. If the owner adopts an idea from an image, update the schedule, scene and affected CAD before issuing the final view.

Before issuing the photographs or compiling a house, run the [photo, adjoining-room and exterior window checks](references/photo-quality.md).

For a completed-value or resale question, run the [two-stage valuation study](references/valuation.md). Freeze the existing and proposed specification and area basis before reconciling dated sold evidence, listing condition and the local house price index.

For a before-and-after brochure or a portable house issue, follow the [property particulars and link verification workflow](references/property-brochure.md).

For complete existing and proposed property editions, use the [property comparison pack skill](../property-comparison-pack/SKILL.md).

Run the [fully dressed walkthrough](references/handover-gates.md#fully-dressed-walkthrough) after the last furnishing change and before releasing the camera.

For the occupant's full sequence of arrival, seating, shared use and departure, use [Living in the Room](../living-in-the-room/SKILL.md).
