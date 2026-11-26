# Household permissions and design decisions

## What the homeowner is willing to change

Ask once up front in ordinary language. “What would you happily let me try, what should I check with you first, and what must stay as it is?” Record relevant interventions separately in the house brief, along with any room or item exception, conditions, source and date. Record their preferred starting point separately from the most disruptive intervention they would entertain. If several options fit, lead with the one that best meets their stated priorities. Keeping a favourite piece can still allow repositioning it. A budget or an interest in major works in one room gives no permission for unrelated changes elsewhere.

| Recorded position | Agent action when activities compete |
| --- | --- |
| Free to explore | Develop the most promising permitted change and compare it with the baseline on the same everyday task. Apply any cost or disruption limits. |
| Ask before exploring | State the specific benefit, drawback and affected spaces. Ask whether to spend design time comparing it. An explicit request for this comparison answers that question. |
| Ruled out or protected | Respect the stated boundary. Test permitted changes such as a different arrangement, product or use. If none meets the brief, show the remaining compromise and ask which outcome matters most. |
| Undecided or unrecorded | Preserve the existing condition, progress the known scope and ask one focused question when the unknown would change the next decision. |

Check a conditional preference against its trigger. If the owner said “only below this cost” and the cost is unknown, obtain an allowance or ask before relying on it. A named room exception takes precedence within that room. If an option affects a second room, check its boundaries too. Ask once where they conflict. If the homeowner revises a limit, date the decision and reopen the affected proposals, product selections and downstream views. Permission to study an option covers its comparison. Record a separate choice before issuing it as selected, ordering or detailing work.

For the same dining-room bottleneck, one household might rule out building work and welcome a smaller table. Test a different table, including its occupied footprint. Another might protect an inherited table but consider moving a fitted cupboard. Keep the table and compare moving the cupboard if authorised. If both items are protected, show how many people can sit and pass together, then ask which use takes priority. Use the same occupied-route check for all three households.

## When to ask the homeowner

At intake, label measured or photographed fabric, explicit homeowner instructions, inferred preferences and illustrative AI content separately. Photographs can show presence and side. A plan or survey establishes dimensions to its stated accuracy. When property sources disagree, identify what to verify. An AI omission cannot establish a removal or a permission to move anything.

Use a decision stop wherever the answer would materially change the proposal:

- **Before proposed CAD**, overlay the concept with existing openings and services. Keep existing fabric in the baseline. For example, “The listing shows the hall door here. Keeping it gives this route. Would you like us to study relocating it as a separate option?” Use this prompt only where an alteration is within the owner’s stated or undecided scope and would serve a stated aim.
- **During layout review**, test a reversible furniture adjustment first. If needs still conflict, show the affected activity and two meaningful choices, with the practical consequence of each. If a missing measurement could settle the matter, request that measurement.
- **Before visual or purchase handover**, check unresolved choices against the reviewed CAD and product evidence. Hold the affected stage if a view would conceal a door or assume a disputed change. Resume only on evidence or an explicit decision for that issue.

Record the source conflict, retained baseline, question, decision owner and affected rooms in the house decision log. Link the entry from the room check. Keep unapproved alternatives separate and continue independent checks. Routine modelling judgements that leave intent and fabric intact can be recorded without interrupting the homeowner.

## At the end of a commission

For a furnished room, first [check the agreed photo and pack](handover-gates.md#finishing-a-furnished-room). A homeowner can accept a room by saying it looks good. Use that reply to continue the agreed issue. Ask about the next commission after releasing the current one, or use a mid-study question for a specific design decision that blocks it.

Show the checked output and explain what it lets the homeowner judge. Read their latest instruction, the aim in their brief and the findings on this revision. Use those to decide who can take the next action.

| What the evidence and instructions tell you | How to respond |
| --- | --- |
| The homeowner asked to see or review something and can now react to it. | Start with an open invitation to say what works or what they would change. In the same turn, offer one or two concrete things they could look at, if useful, and explicitly offer to move on to another priority or pause. Give them one opportunity to reply in their own words. |
| Progress on the requested work depends on a household preference or permission. | Ask the specific question directly. Say what each feasible choice changes for the household. If they move on, record which part is still open and continue independent work. |
| The homeowner already chose the next deliverable. | Carry the instruction forward. Give them room to comment on the result as you continue the agreed work. |
| A measurement, quote clarification or professional finding is outstanding. | Record the missing fact, who can provide it and what it affects. If the homeowner can respond to the work already shown, invite that feedback. Ask them about the outstanding item only when they can supply the fact or make a meaningful choice. |

Pick prompts the homeowner can answer from their experience and the issued evidence. Use their own priorities and the consequence for them. For a garden study commissioned for an evening meal, the shade drawing might prompt feedback about when they sit outside or which spot they would use. For a quote comparison requested around disruption, the useful follow-up might be whether the proposed weeks without a bathroom would work for them. A missing allowance still goes back to the builder. The brief and the findings determine which prompts are worth offering. When suggesting another study, say what the homeowner would receive.

Save the complete invitation and any optional suggestions together with `--ask`. Record their actual reply with `house.py answer` and carry it into the affected brief and decisions. Keep routine follow-up with its owner in `--next`.

### Show the choice

For a question about placement, service routes, door swings, views or finishes, put a legible image directly beside the question. Use a crop of the checked plan, an annotated source photograph or a like-for-like comparison. Label the choices in household language such as “kitchen side” and “radiator side”. Show the chair pulled out or the door open if that is what creates the choice. Give one shared scale and orientation for layout alternatives. Use labels or line patterns alongside colour and describe the finding in text for readers who cannot see the image.

Display the image before a text-only question form. A link to the pack can follow for detail. During a render hold use the authorised CAD drawing. Keep text-only questions for choices such as dates or spending limits where an image adds little. Save the image under the current revision and pair `--ask-image` with `--image-description`. [Revision commands](../../../docs/output-revisions.md#record-the-next-homeowner-choice)
