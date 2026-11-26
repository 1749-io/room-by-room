# Before-and-after particulars and portable delivery

Start with the address-matched property description prepared before pricing. Check the existing listing photographs, original marketing plan, dated particulars and the official EPC for that exact address. Record certificate number, expiry, assessed floor area, score and potential. Keep the proposed scheme's energy performance open until a new assessment exists.

Pair each existing photograph with a clearly labelled design view. Describe accommodation and use, garden, parking lost or gained, area on a common basis, tenure, council tax, heating, access, location and material information still to confirm. Distinguish the advertised price, dated completed-scheme appraisal and any achieved sale. Give source links. Inspect the rendered PDF at reading size and provide a browser edition.

Use one private revision for each issue. Keep the original signed room archives intact. Give every room a readable HTML entry. Label archive links as downloads and provide browser reading routes for key PDFs. Include a human-readable link register with each destination's name, purpose, format and issue, plus Link-register.csv with label, purpose, path and sha256 columns. Point both the local dashboard and extracted Start here.html to the same current issue.

Run `python tools/check_delivery.py PACK.zip` on the built ZIP. Extract it in a separate directory and run `python tools/smoke_pack_browser.py "EXTRACTED/Start here.html"` with Playwright Chromium installed. Check linked PDFs, room count, visual evidence and open survey items separately. CI runs a portable fixture on Windows and Linux. Keep real homeowner data out of CI fixtures.

When a historic camera has no structured review, compare its registered source and photo. Save photo-reviews/<room>-brief.json and photo-reviews/<room>.json in a new revision and then point rooms/<room>/photo-review-addendum.json at its revision and source_revision. Retain superseded photos as historical evidence. Distinguish a resolved design sightline from actual fit, exterior lining, privacy glass or fixing confirmation.

For a corrected pair, put both reviewed images in the saved addendum. Its photo entry names those files, their hashes and the original registered photo and camera under `replaces`. Check each visible neighbouring room again, keep previous sources traceable and carry independently open survey items forward.
