# Eight decisions a homeowner can work through

These are fictional desk exercises. Each starts from a household preference and has enough information to follow the decision by hand. Carry the method into a house using its own measurements, prices, people and permissions.

## 1. Will a flush patio send rain towards the kitchen?

**Evidence.** The owner wants a step-free route to the table. At the doorway the existing paving is at the survey datum of 0 mm. At a point 2,000 mm into the garden it is +40 mm. The proposed drawing keeps these levels. The gully beside the door has no recorded outlet.

**Work it through.** Along this section water would run down towards the door, with a 40 mm fall over 2 m. A level-looking threshold in an image would hide that fact. Ask the surveyor for threshold and adjacent ground levels on the same datum, and the drainage designer to trace the outfall and resolve the detail. Keep the accessible approach in the brief and hold the paving levels. A different outfall or a crossfall elsewhere could change the design. For an English site the area flood map adds context to the level survey. [Environment Agency service](https://www.gov.uk/check-long-term-flood-risk)

## 2. Will a visitor manage the downstairs shower?

**Evidence.** A visitor's aid passes a straight hall. The room itself has a return, a threshold and a door leaf that occupies the approach when open. The family would consider moving loose storage but wants the existing door retained.

**Work it through.** Replay the existing walking-aid test. Read which part of the route remains unverified even where a circular envelope passes. Measure the actual aid, turning space, threshold and door operation with the intended user. Try the permitted storage move. Issue a viewing measurement while the turn remains unresolved. [Route tests](../tests/test_routes.py) · [Interpretation of route results](../skills/freecad-renovation/references/route-studies.md)

```sh
python -m unittest discover -s tests -p test_routes.py -k walker_needs -v
```

## 3. Can we keep a working bathroom during the refit?

For the full house example, compare [five programmes, including a delayed handover](whole-house-changes/README.md#3-which-bathroom-works-tonight).

**Evidence.** A household needs a working WC and shower every night. Its only two showers share a water riser. The first quotation schedules demolition in both rooms on Monday and restoration on Friday.

**Work it through.** Monday to Thursday nights fail the brief. Reorder the packages so the first bathroom is back in use and tested before the second comes out. Ask the plumber whether the first bathroom can run during the second isolation. If the common riser prevents it, show the actual outage and price temporary facilities or nights away. The first handover is a demonstrated working shower and WC. That result decides the second start date.

## 4. Which builder has actually priced the same kitchen?

Carry this comparison through the [whole-house ceiling and occupied works allowance](whole-house-changes/README.md#2-which-builder-fits-the-house-budget).

**Evidence.** Quote A is £48,000 and excludes electrical work and making good. Quote B is £52,000 and includes both. Both include VAT on the quoted scope. The owner's like-for-like allowances are £3,600 and £1,800 including VAT. Both omit the same appliances.

**Work it through.** Put the two missing allowances against A once. A is £53,400 on the comparison basis and B is £52,000. B is £1,400 lower on that basis. A's allowances can still change. Ask A for fixed inclusions and both contractors for matching specifications, exclusions and programme. Carry appliances once in the owner-supplied package. Record the validity date before choosing.

## 5. Can a cheaper replacement fridge go straight on the order?

**Evidence.** The joiner has designed a 900 mm opening. Model A is 860 mm wide and its installation drawing requires 15 mm at each side. The substitute B is 880 mm and its drawing requires 20 mm at each side. Buying either is within budget.

**Work it through.** A needs 890 mm. B needs 920 mm and exceeds the opening by 20 mm. Reject B for the current joinery. Reopen the product and cabinet records if the owner wants it enough to change the run. Check the delivered route, hinge side, door opening, ventilation and connections before ordering A. Retain the exact installation drawings in the house records.

## 6. Will the retrofit leave enough room for the desk?

**Evidence.** An office is 2,800 mm across. Its desk, occupied chair and the household's agreed passage use 2,710 mm on the coordinated plan. A proposed internal lining on one wall is 110 mm thick including the finish. The owners want to keep the desk.

**Work it through.** The finished width becomes 2,690 mm, 20 mm short. Draw the finished face, reposition the desk within the permitted scope and rerun the occupied route. Ask the retrofit designer to resolve the wall build-up, moisture at junctions, ventilation and heat-loss implications before a thinner system is assumed. Keep both the room-use finding and the envelope decision open until they work together.

## 7. Is the music room quiet enough for an evening call upstairs?

**Evidence.** The household accepts music until 21.00 and wants speech intelligible in the upstairs office on calls until 20.00. Both rooms work individually. A trial with the actual speakers and both doors closed leaves the music audible on the recorded call at the usual listening volume.

**Work it through.** There is an hour of conflicting use. Agree a repeatable listening level, call position, door state and ventilation setting, and repeat with the speakers in a permitted alternative position. If the call still fails, ask whether to change the timetable or commission an acoustic assessment of doors, ducts, floors and flanking paths. Record the conditions in both room briefs. A plan distance or a lining catalogue alone cannot settle this choice.

## 8. Does a solar quote save what the brochure implies?

**Evidence.** A fictional roof study estimates 3,000 kWh AC a year. The household's time-matched usage model gives 1,200 kWh consumed on site and 1,800 kWh exported. For this arithmetic example only, import is 25p/kWh, export 5p/kWh and the owner-supplied installed quote is £6,000.

**Work it through.** Avoided import is £300 a year and export income £90. At those fixed assumptions simple payback is about 15.4 years (£6,000 ÷ £390), before degradation, maintenance, financing or tariff changes. The next decision is whether a verified layout, shading study and the household's actual interval data justify getting a comparable quote. A rooflight that removes a module reopens both the roof drawing and yield calculation. [Roof study inputs](../skills/renovation-pack/references/specialist-design-tools.md#rooftop-solar)
