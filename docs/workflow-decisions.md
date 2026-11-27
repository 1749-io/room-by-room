# Decisions, questions and return paths

Use this guide beside the [full workflow diagram](workflow.svg) or the [quick reference](workflow-quick.svg). The seven room reviews in `review.csv` are brief, existing-cad, proposed-cad, blender, products, final-ai and handover. The other decisions below apply when the work calls for them. Each room pass records the revision, reviewer, finding and inspectable evidence.

[Brief and revision](#brief-permissions-and-revisions) · [Occupied CAD](#existing-building-and-occupied-proposal) · [Furnishing and final images](#furnishing-colour-and-final-photography) · [Issue and works](#issue-shared-costs-and-later-work) · [Specialist triggers](../skills/renovation-pack/references/specialist-design-tools.md#requests-that-trigger-a-specialist-study) · [Worked support-beam example](#worked-example--a-support-beam-over-the-kitchen-opening)

## Brief, permissions and revisions

### Brief · Do we know enough for the next decision?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack and house.py start, list and add-room capture the original sources, household routines and budget. The checklist, status and history commands bring survey evidence and outstanding reviews together. |
| Check | On a new house, preserve the original brief, plans and photos. Create CHECKLIST.md at intake. On resuming, read it with history, dashboard, brief, decisions and room reviews. Record household routines, shared seats and routes, retained pieces, shopping, budget and commissioned outputs. |
| Next review or output | Scope / Existing CAD / Buyer assessment |
| Return destinations | Brief |
| Proceed | Pass the brief for the relevant study. A buyer or desk assessment can finish with the evidence, uncertainty and next viewing or survey check. A whole-house commission also opens the shared decision record. |
| Return | If sources conflict, retain observed fabric in the baseline. Identify the evidence that could settle the conflict. Work on independent rooms or the retained option while it is open. |
| Ask | Ask the homeowner only about a gap that changes what happens next. Which activities must work together? What must stay, what may move, and which choices may the agent make? |

### Scope · May we explore this particular change?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack checks household permissions against the room brief. Use house.py next, ask and answer to show the labelled choice and record the decision. |
| Check | Read house limits and room exceptions on both sides of a shared route. Check the budget or disruption conditions attached to any permission. Screen each new request, follow-up or changed constraint for an explicit or implied specialist question. |
| Next review or output | Existing CAD / Specialist study |
| Return destinations | Scope / Brief |
| Proceed | Explore a permitted change. For a triggered specialist study, give its owner the question, source revision and allowed options. Return the finding to the relevant decision and rerun the affected checks. |
| Return | Keep a protected item or ruled-out intervention in place. Try a permitted alternative. Where permission is unknown, continue the baseline. Permission to compare an option still leaves its selection open. |
| Ask | If the owner reserved the choice, show the benefit, drawback and affected rooms before modelling. “Keeping this doorway narrows the route. Would you like to compare moving it?” Record the answer and its limits. |

### Revision · Is the evidence safe to publish?

| Route | What happens |
| --- | --- |
| Tools | Use house.py begin-revision, save-revision and verify-revision to preserve inputs, outputs and their history. The backup and restore commands support recovery. |
| Check | For each new or revised output, use begin-revision. Capture the governing instructions and inputs. Work in the printed private directory, reopen the result and inspect it in its owning tool. If MCP disconnects, reconnect and inspect the actual document before retrying. |
| Next review or output | Saved output |
| Return destinations | Revision |
| Proceed | Use save-revision with inputs, change, reason, author, effects and next action. The save verifies a whole-house backup before publication. Link the saved output to the review. Report a failed design as a measured finding. |
| Return | If backup verification fails, keep the draft, correct the cause and retry the same save. If published evidence changes or the wrong revision is supplied, hold its review, recover or create a new revision, and recheck dependent outputs. |
| Ask | The agent resolves file, connector and backup problems. Seek an owner decision only if resolving the work would change the brief. On another computer, restore the matching house backup to open private files. |

## Existing building and occupied proposal

### Existing CAD · Does the saved shell fit the sources?

| Route | What happens |
| --- | --- |
| Tools | FreeCAD MCP builds and reopens the measured shell. BIM and TechDraw show levels, openings and sections. IfcOpenShell checks supplied IFC units and placement. Resolve survey discrepancies against the original evidence. |
| Check | FreeCAD MCP reopens the baseline. Compare scale, axes, storeys, openings, stairs, services and obstructions with photos, plan and sections. Mark provisional measurements. Assess actual routes through occupied thresholds and report their limiting pinch. |
| Next review or output | Furniture study / Proposed CAD / Buyer assessment |
| Return destinations | Existing CAD / Scope |
| Proceed | Pass existing-cad for the intended decision. A measured assessment may end here. A proposal uses its own revision. An optional unrendered furniture study can branch off the checked shell. |
| Return | Correct missing or wrongly placed fabric in existing CAD and reopen the model. If a missing dimension could reverse the fit, record the measurement needed and hold that fit. A concept image cannot authorise removal of observed fabric. |
| Ask | The surveyor establishes a disputed dimension or concealed condition. Ask the homeowner before exploring a change to retained fabric unless the relevant permission is already recorded. |

### Furniture study · Is an unrendered study useful and permitted?

| Route | What happens |
| --- | --- |
| Tools | Run house.py check-study on the shell revision. Blender MCP places dimensioned furniture in the unrendered scene. The room asset library builds each candidate at its stated size and reads the size back. Return candidate positions to FreeCAD for the occupied test. |
| Check | Run check-study with the actual shell revision and inspect the visual instructions. A render-only hold permits an otherwise authorised viewport study. CAD-only or all-visual instructions keep exploration in FreeCAD. |
| Next review or output | Proposed CAD |
| Return destinations | Existing CAD / Furniture study |
| Proceed | Blender MCP locks the transferred shell and checks units, orientation and two landmarks. Try placements at the entrance and seated eye height. Return item IDs, positions, rotations, fronts and units to proposed FreeCAD. |
| Return | For a stale shell, reversed transfer or incorrect scale, correct the transfer and repeat the check. If the study is outside scope, proceed directly to permitted CAD work. A candidate still needs an occupied layout review. |
| Ask | If the use of a seat changes the decision, ask who needs the view, conversation or reach. The agent can try arrangements within the existing permission without another approval. |

### Proposed CAD · Does the whole room work in use?

| Route | What happens |
| --- | --- |
| Tools | FreeCAD MCP and TechDraw show the occupied plan and sections. Shapely and GEOS measure clearances. NetworkX traces connected journeys. Use check-routes, check-openings and check-layout against the current geometry. |
| Check | On one reopened CAD plan show intent, use, journey and whole-room findings together. Test every declared position, actual shared furniture outline, operating fronts, seat views, reach, door swings and simultaneous routes. Check sections for height. Compare permitted options on the same routine. For a highly glazed space, review external shadows, seated glare, summer heat and winter cold before furnishing. |
| Next review or output | Visual permission / CAD-only issue |
| Return destinations | Scope / Proposed CAD / Existing CAD |
| Proceed | Record the selected option or delegated choice. Pass proposed-cad and run check-layout with the actual revision. Issue a checked CAD-only plan if commissioned. A diagnostic issue can show a failed option and the measured reason for its hold. |
| Return | On a pinch, try the least disruptive permitted adjustment, then repeat the occupied check and linked room journeys. A specialist’s returned support, threshold, service or product size reopens the same checks and any dependent quote or order. |
| Ask | Use house.py ask to check the labelled occupied plan and present it inline with the question. “Would you prefer to keep this cabinet or pass behind eight diners?” Mark both options on the plan. Record the reply or the measurement that will settle it, then retest. |

## Furnishing, colour and final photography

### Visual permission · Can this camera be furnished and rendered?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack reads the homeowner’s scope and house.py check-render checks the input revision and render hold before the camera or final image. |
| Check | Check the actual selected revision, current look and homeowner holds. Run check-render for blender before the furnished camera. A render hold pauses rendered cameras, AI and publication. A broader visual hold also pauses viewport work. |
| Next review or output | Blender |
| Return destinations | Visual permission / Proposed CAD |
| Proceed | With the fit accepted, look agreed and render released, furnish the full room in Blender. Where the look is open, use permitted swatches, colour advice or an authorised styling study before sourcing. |
| Return | Keep a held visual pending. Return a changed item to the shopping schedule and native scene. If its fit, access or use changes, return to occupied CAD, then repeat transfer and camera checks. |
| Ask | “Which of these finishes should we carry forward?” Use an existing delegation where it covers the choice. If the homeowner paused a visual, record the release for that particular work before resuming. |

### Blender · Does the reopened camera show the selected room?

| Route | What happens |
| --- | --- |
| Tools | Blender MCP places and counts the selected objects. A room asset library stand-in represents a selected product only where it matches that product's distinctive form. After the last accessory, reopen the scene. Living in the Room uses the route solver and opening measurements before the camera is rendered. |
| Check | Match CAD units, axes, two identifiable features, boundaries and openings. Trace each seat approach and exit with adjacent places occupied. Test plants, door travel and cupboard access. Once the walkthrough passes, render and inspect the named camera and reverse view for placement, clipping, hidden items and light. |
| Next review or output | Products |
| Return destinations | Blender / Existing CAD / Proposed CAD |
| Proceed | Pass the blender review for that scene and camera. Pass the named object list, reviewed camera, reverse view and asset provenance to the product review. |
| Return | Correct a transfer, misplaced object, incomplete dressing or clipped view in Blender. If the source opening or selected arrangement is wrong, correct existing or proposed CAD first and repeat the downstream reviews. |
| Ask | Fix ordinary camera and modelling errors directly. If the view depends on hiding a disputed door or adopting a different arrangement, hold it and take the design choice back to the homeowner. |

### Products · Do the variants, lighting and palette pass together?

| Route | What happens |
| --- | --- |
| Tools | Blender compares the actual variants, lighting and palette with the shopping schedule. Colour Expert can help resolve open choices. An optional AI styling study can inform sourcing. |
| Check | Reconcile every selected or reused shopping ID, quantity, exact variant and dimensions against the reopened native objects. Check out-of-frame items separately. Compare supplier references in neutral light, then inspect the same camera under the proposed lighting. Record a room-palette finding for every furnished room. |
| Next review or output | Final AI |
| Return destinations | Products / Blender / Visual permission / Proposed CAD |
| Proceed | Pass products with the current evidence. Check-render for final-ai against the actual input revision and any explicit AI hold before sending the reviewed camera and product references to the image editor. |
| Return | Correct a wrong material, variant, count or light in the scene and repeat the camera and product checks. If a substitute changes fit, return to CAD. If identity cannot be verified, keep the affected finish view on hold. |
| Ask | If a consequential palette choice remains, show the options under consistent light. Record the owner’s choice or delegated decision and repeat the furnished-room palette check. A suggested minor improvement can accompany a pass. |

### Final AI · Does this photo match this exact camera?

| Route | What happens |
| --- | --- |
| Tools | Reference-image editing uses the checked Blender camera and product references. Compare the photograph beside that camera and run check-room-photos on the required views. |
| Check | Compare each generated photo beside its reviewed Blender camera and product references. Compare the intended door mechanism with both views. Inspect seat access, counts, fronts, clearances, finishes, lighting and colours. Record an ai-colour finding per issued camera. |
| Next review or output | Handover |
| Return destinations | Final AI / Blender / Proposed CAD / Existing CAD |
| Proceed | Pass final-ai for that camera and take the reviewed pair into the commissioned presentation. Keep rejected images outside the issue. |
| Return | Retry image-only drift from the original reviewed camera. For a scene or product error, fix Blender and repeat the product and camera checks. For wrong fabric or an incorrect arrangement, return to CAD and recheck dependent work. |
| Ask | If the owner wants an idea introduced by the AI, record the choice, source and model it, recheck fit where affected, then generate a new final photo. |

## Issue, shared costs and later work

### Consent · What evidence permits this alteration to advance?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack uses the nation-specific consent enquiry, authority records and the proposed FreeCAD drawing to identify which permissions and replies the alteration needs. |
| Check | A new opening, change of use, frontage, boundary or shared service can trigger an enquiry. Match the plot, nation, authority, proposal revision, relevant rights, decision notices and conditions. Check the building-control route for the actual intervention. |
| Next review or output | Whole house / Buyer assessment |
| Return destinations | Consent / Scope |
| Proceed | Record the dated evidence, its status and permitted next use. A buyer can receive the outstanding enquiries. Carry any actual permission and its conditions into the coordinated design and programme. |
| Return | If the plot, decision or condition is uncertain, request the record and hold dependent commitments. If the design changes, revisit the applicable enquiry, cost and affected rooms. |
| Ask | The planning authority, building-control professional, solicitor or surveyor resolves the specific question. Ask the homeowner whether to pursue a permitted alternative only when that choice changes the design or spend. |

### Decorator · Is each requested surface ready to specify?

| Route | What happens |
| --- | --- |
| Tools | Colour Expert and the surface schedule bring together shade, sheen, sample and approval. Run house.py check-decorator before issuing finishes. |
| Check | This branch can start from the brief independently of renders. Check one entry per scoped surface, manufacturer, named colour, finish, code where supplied, revision and sample approval or explicit instruction. Run check-decorator on that revision and surface scope. |
| Next review or output | Decorator issue |
| Return destinations | Decorator / Products |
| Proceed | Issue the approved surface schedule. A concept can separately identify outstanding sample decisions. |
| Return | Hold a surface with a missing specification or sample decision. Compare the physical sample against retained finishes in the relevant light, update the schedule and repeat the scoped check. |
| Ask | The homeowner or delegated approver confirms the physical finish where a sample is required. Record the actual approval before issuing instructions for that surface. |

### Whole house · Can the affected package be priced, ordered or phased?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack connects affected rooms, shared routes, quotes, orders and budget. Python tender comparisons and a shopping workbook reconcile quantities, exclusions and allowances. |
| Check | Track shared structure, services, consent, surveys, costs and occupancy on the dashboard. Use the same revision for tender comparisons. Reconcile VAT, exclusions, provisional sums, delivery, substitutions and reserve. Check access, cooking, WC, washing and heat in each affected phase. |
| Next review or output | Priced package / Occupied works |
| Return destinations | Whole house / Proposed CAD / Consent |
| Proceed | Carry the approved scope and outstanding holds to the budget, shopping list, bidders and programme. Release a dependent order only with its required measurements, decisions and procurement authority. |
| Return | A changed pier, price, delivery or service handover can reopen several rooms. Update impacted drawings and orders, rerun routes, reprice like for like and reschedule dependent trades. Unaffected work can continue. |
| Ask | Ask about budget or occupation when it changes the viable options. “Must you stay here throughout, and which facilities must work each night?” The engineer, installer or authority resolves technical or consent questions. |

### Handover · Can each recipient open and rely on the issue?

| Route | What happens |
| --- | --- |
| Tools | Use house.py checklist and save-revision to issue the reviewed work. For a photo pack, check-room-photos and check-house-photos verify the evidence, then pack-house-photos assembles it. PDF and workbook tools prepare the recipient files. |
| Check | Inspect the actual exported drawings and presentation. Reopen the native files, test the named camera where commissioned, compare image pairs, reconcile quantities and costs, extract the archive and check the recipient’s scope. |
| Next review or output | Issued pack / Completion |
| Return destinations | Handover / Affected review |
| Proceed | Check each visible window covering, including its outside face through other windows. Verify the final photo against its camera and its bytes inside the room pack before inviting another study. Carry purchase-only holds to the shopping schedule. For an expressly shorter commission, deliver its checked buyer, CAD, camera or decorator output. Refresh CHECKLIST.md with the reviewed outputs, homeowner acceptance and owners of outstanding returns. |
| Return | If a file, image, price, revision or quantity disagrees, return to its owning stage, correct it and reopen affected reviews. For a survey return, link the measurement and the repeated design check in the survey register. Repackage, extract and examine the issue again. Keep a withdrawn issue identifiable. |
| Ask | Show the issued work and use the [handover question guidance](../skills/renovation-pack/references/homeowner-decisions.md#at-the-end-of-a-commission). Invite a reaction to a review or ask about the specific choice that blocks progress. Record their reply and follow an existing instruction. |

Where the commission extends to construction, record variations, as-built changes, tests, warranties and snags. An installed difference goes back to the affected drawing, cost or commissioning check before close-out.

### Occupied works · Is the next construction phase ready?

| Route | What happens |
| --- | --- |
| Tools | The local Python programme checks facilities and access night by night. Use OpenProject for trade dependencies when the project workspace is available. |
| Check | Apply this branch when the appointment covers the works. Test the facilities the household needs, including the actual route to them at the time of use. Identify shared isolations, deliveries, access and any temporary arrangement. |
| Next review or output | Next phase / Completion |
| Return destinations | Occupied works / Whole house |
| Proceed | Once the plumber or trade demonstrates the handover and the household can use the facility, release the dependent phase. Record what was demonstrated, by whom and what remains open. |
| Return | If the working bathroom, safe access, heat or another agreed facility is unavailable, delay the dependent strip-out. Rebook the trade or price temporary arrangements and send the change back to the budget and programme. |
| Ask | The site lead verifies access and the trade verifies the service. Ask the homeowner whether a proposed interruption or nights away are acceptable when a workable sequence depends on that choice. |

### Completion · Is the installed result recorded and usable?

| Route | What happens |
| --- | --- |
| Tools | Renovation Pack reconciles as-built returns, commissioned tests, warranties and snags. FreeCAD records verified changes. The checklist and revision history retain the accepted issue. |
| Check | When appointed through construction, reconcile installed work with the approved variation, as-built drawing, commissioning results, warranties, controls and access for maintenance. Inspect outstanding snags with their owners. |
| Next review or output | Owner records |
| Return destinations | Completion / Affected review |
| Proceed | Hand over the usable owner records, status of outstanding works and maintenance information. Close an individual snag after its correction has been checked. |
| Return | An as-built discrepancy, failed test or inaccessible control returns to its designer or installer. Update the record, repeat the affected test and reissue corrected owner information. |
| Ask | The responsible installer or professional verifies the work. The homeowner decides any material change of scope, cost or finish through the recorded variation process. |

## Worked example · A support beam over the kitchen opening

### Opening enquiry · What does the engineer need to return?

| Route | What happens |
| --- | --- |
| Tools | FreeCAD BIM and TechDraw overlay the storeys and section the opening. For a commissioned analysis with verified inputs, PyNite models the beam or frame and FreeCAD FEM runs CalculiX to inspect stress and deflection. Return support dimensions to the occupied plan. |
| Check | “Can we open the kitchen up?” triggers a structural review even if nobody mentions a beam. Overlay the affected storeys and cut a section through the proposed opening. Identify the upper wall, floor and roof, unknown bearings, supports below, cabinets and routes. |
| Next review or output | Engineer enquiry / Proposed CAD |
| Return destinations | Existing CAD / Proposed CAD / Whole house |
| Proceed | Send the measured-survey and opening enquiry to the engineer. Request the finished positions and sizes of piers or posts and the clear height below the beam. Put the returned geometry into both daily and eight-person layouts. |
| Return | Where the support position or load path is unresolved, hold the dependent set-out, kitchen order and coordinated pricing until the return is checked. |
| Ask | The engineer establishes how the load will be carried. If the returned design conflicts with dining or storage, the homeowner chooses between the permitted layout changes after seeing their consequences. |

### Orchard House · What changes after a support is returned?

| Route | What happens |
| --- | --- |
| Tools | FreeCAD MCP inserts the returned pier. Shapely and NetworkX retest the occupied route. The tender comparison and bathroom programme carry the resulting cost and timing into the house decision. |
| Check | In the fictional replay the pier face moves 300 mm west. The occupied route drops to 646 mm for four and eight diners against the household’s 825 mm serving target. Withdraw the old cabinet set-out from pricing. |
| Next review or output | Whole house / Priced package |
| Return destinations | Proposed CAD / Whole house |
| Proceed | Shorten the end unit, shift the table and move the dry prep bench. At R3 the routes reach 945 mm for four and 845 mm for eight. Take the storage choice to the owner, send both bidders the same plan and check the site before ordering. |
| Return | Shortening the cabinet alone restores a 950 mm straight gap, yet eight diners still leave only 666 mm on the continuous route. Repeat the occupied test at each change. Carry the selected scope and any cost of staying at home into the tender comparison. |
| Ask | “Would you move the displaced storage to the utility?” In the separate fictional beam benchmark, the hand check and PyNite give 0.91553 mm of midspan movement. The fine CalculiX mesh gives 0.91868 mm. A live beam design requires the engineer’s site-specific inputs and interpretation. |

[Orchard House replay](../examples/whole-house-changes/README.md) · [Two-solver support-beam benchmark](../examples/structural-opening/README.md)
