"""Resolve a commissioned room issue against captured inputs and current reviews."""
import csv
import hashlib
import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

import house_revisions as revisions

COMPONENTS = ("room-review", "drawing", "shopping")
EDITIONS = {"homeowner-presentation": ("room-review", "shopping"),
           "architect-pack": ("drawing",), "buyer-brief": ("drawing", "shopping")}
SCHEDULES = {"decorator-finishes": "Decorator finishes", "cost-schedule": "Cost schedule", "programme": "Programme"}
CAD_STAGES = ("existing-cad", "proposed-cad")


def required(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Enter {key} in the pack request")
    return value.strip()


def read_request(path):
    req = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(req, dict) or req.get("version") != 1:
        raise ValueError("Expected a version 1 component request")
    for key in ("house", "audience", "purpose", "limitation", "next_action"):
        required(req, key)
    profile = req.get("profile", "room")
    if "editions" in req and profile != "house":
        raise ValueError("Name saved editions in a house request")
    if "omissions" in req and profile != "edition":
        raise ValueError("Declare scoped source omissions in an audience edition")
    parts = req.get("components")
    sharing = req.get("share_with", [])
    if not isinstance(sharing, list) or any(not isinstance(a, str) or not a.strip() for a in sharing):
        raise ValueError("share_with must list the additional named recipients")
    if profile == "schedule":
        if not isinstance(parts, list) or len(parts) != 1 or parts[0] not in tuple(SCHEDULES):
            raise ValueError("Select one schedule: " + ", ".join(SCHEDULES))
        return req
    if profile == "edition":
        if not isinstance(parts, list) or len(parts) != 1 or parts[0] not in tuple(EDITIONS):
            raise ValueError("Select one audience edition: " + ", ".join(EDITIONS))
        required(req, "editorial")
        if not isinstance(req.get("rooms"), dict) or not req["rooms"]:
            raise ValueError("Declare the saved room sources for the audience edition")
        return req
    if (not isinstance(parts, list) or not parts or any(p not in COMPONENTS for p in parts)
            or len(parts) != len(set(parts))):
        raise ValueError(f"Select distinct components from {', '.join(COMPONENTS)}")
    if req.get("profile", "room") == "house":
        if not isinstance(req.get("rooms"), dict) or not req["rooms"]:
            raise ValueError("Declare source issues for each registered room")
        editions = req.get("editions", {})
        if not isinstance(editions, dict) or any(k not in (EDITIONS | SCHEDULES) or not isinstance(v, str)
                                                 for k, v in editions.items()):
            raise ValueError("Choose a recognised house edition")
        return req
    if req.get("profile", "room") != "room":
        raise ValueError("Choose the room, edition, schedule or house delivery profile")
    required(req, "room")
    if set(parts) & {"drawing", "room-review"}:
        for key in ("source_revision", "sheet_id", "sheet_title", "sheet_caption", "scale_basis"):
            required(req, key)
        if req.get("stage") not in CAD_STAGES:
            raise ValueError("Choose existing-cad or proposed-cad for the drawing basis")
    if "room-review" in parts:
        required(req, "daily_use")
        if req.get("room_scope") not in ("cad-review", "furnished"):
            raise ValueError("Choose cad-review or furnished for the room commission")
    return req


def context_files(root, req):
    import house
    if req["house"] != revisions.stored_json(root / "project.json")["id"]:
        raise ValueError("The request belongs to a different house")
    if req.get("profile") == "house":
        return []
    if req.get("profile") == "schedule":
        from tools.schedule_data import inputs_for
        return inputs_for(root, req)
    if req.get("profile") == "edition":
        from tools.audience_packs import editorial_inputs
        from house_visuals import REGISTERS
        visual = any(isinstance(row, dict) and set(row) & {"drawing", "room-review"} for row in req["rooms"].values())
        return [*editorial_inputs(root, req), *(REGISTERS if visual else ())]
    room = "rooms/" + house.identifier(req["room"])
    if not revisions.local_path(root, room + "/review.csv").is_file():
        raise ValueError(f"Unregistered room: {req['room']}")
    files = []
    if set(req["components"]) & {"room-review", "drawing"}:
        from house_visuals import REGISTERS
        files.extend((room + "/README.md", room + "/review.csv", *REGISTERS))
        if req.get("sheet_source"):
            files.append(room + "/layout-checks.csv")
    if "shopping" in req["components"]:
        files.append("shopping.csv")
    return files


def digest(path):
    with path.open("rb") as stream:
        return revisions.transfer(stream)


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def shopping_rows(path, room):
    import house
    selected = []
    ids = set()
    slug = house.identifier(room)
    for row in read_rows(path):
        source_rooms = {house.identifier(label.strip()) for label in (row.get("room") or "").split("/") if label.strip()}
        if slug not in source_rooms:
            continue
        item = row.get("item_id") or row.get("guide_ref")
        product = row.get("product_and_variant") or row.get("product_name")
        if not item or item in ids or not product or not row.get("status", "").strip():
            raise ValueError(f"{room}: missing or repeated item ID, variant or status at {item!r}")
        ids.add(item)
        try:
            qty = Decimal(row["quantity"])
            price = Decimal(row["unit_price_gbp"]) if row.get("unit_price_gbp") else None
            if not qty.is_finite() or qty < 0 or (price is not None and not price.is_finite()):
                raise ValueError
        except (KeyError, TypeError, InvalidOperation, ValueError) as exc:
            raise ValueError(f"{item}: invalid quantity or unit price") from exc
        shared = len(source_rooms) > 1
        holds = [row.get(k) for k in ("fit_hold", "current_fit_hold", "full_fit_hold") if row.get(k)]
        if shared:
            holds.append("Shared item. Purchaser to confirm this room's allocation before ordering.")
        dimensions = row.get("dimensions") or ", ".join(
            f"{label} {row[label+'_mm']} mm" for label in ("width", "depth", "height", "length", "diameter")
            if row.get(label+"_mm"))
        selected.append({
            "Item ID": item, "Selected product and variant": product, "Quantity": "" if shared else str(qty),
            "Source rooms": row["room"], "Source quantity": str(qty),
            "Selection status": row["status"], "Finish / specification": row.get("finish") or row.get("specification", ""),
            "Dimensions": dimensions,
            "Unit GBP": str(price) if price is not None else "",
            "Quantity x unit GBP": str((qty * price).quantize(Decimal("0.01"))) if price is not None and not shared else "",
            "Price date": row.get("price_date") or row.get("reference_date", ""),
            "Price basis": row.get("price_basis", ""),
            "Fit / purchase hold": " / ".join(dict.fromkeys(holds)) or "Confirm purchase readiness before ordering.",
            "Supplier": row.get("supplier_url") or row.get("url", ""),
        })
    if not selected:
        raise ValueError(f"No shopping rows match the registered room {room!r}")
    return selected


def design_evidence(root, inputs, req, slug):
    import house
    room = root / "rooms" / slug
    register = room / "review.csv"
    stage = req["stage"]
    rev = revisions.revision_id(req["source_revision"])
    through = "handover" if "room-review" in req["components"] and req["room_scope"] == "furnished" else stage
    rows = house.review_rows(register)
    passed, reason = house.status_through(root, register, rows, through)
    if not passed:
        raise ValueError(f"{slug}: {reason}")
    frozen = {r["stage"]: r for r in read_rows(inputs / "rooms" / slug / "review.csv")}
    stages = {r["stage"]: r for r in rows}
    for row in rows:
        if row != frozen.get(row["stage"]):
            raise ValueError(f"{slug}: {row['stage']} review changed. Begin a fresh issue.")
        if row["stage"] == through:
            break
    entry = stages[stage]
    if entry["revision"] != rev:
        raise ValueError(f"{slug}: {stage} uses {entry['revision']}, requested {rev}")
    sheet = req.get("sheet_source") or entry["evidence"]
    if sheet != entry["evidence"]:
        checks = room / "layout-checks.csv"
        def approved(path):
            return any(r["revision"] == rev and r["result"] == "pass" and r["evidence"] == sheet
                       for r in read_rows(path))
        if stage != "proposed-cad" or not approved(checks) or not approved(inputs / "rooms" / slug / checks.name):
            raise ValueError(f"{slug}: select the reviewed drawing for the requested CAD stage")
    if not sheet.startswith(f"revisions/{rev}/outputs/"):
        raise ValueError("The checked sheet must belong to the named saved design revision")
    path = revisions.local_path(root, sheet)
    if path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Link a reviewed drawing export from the CAD review or layout checks")
    assets = {"sheet": path}
    captions = {}
    if through == "handover":
        import house_photos
        output = revisions.record_dir(root, rev) / "outputs"
        review = house_photos.review(output, room, rev)
        for number, photo in enumerate(review["photos"], 1):
            folder = output
            if "replaces" in photo:
                correction = revisions.stored_json(room / "photo-review-addendum.json")["revision"]
                folder = revisions.record_dir(root, correction) / "outputs"
            for role in ("camera", "photo"):
                key = f"{role}-{number}"
                assets[key] = revisions.local_path(folder, photo[role])
                captions[key] = photo["composition"]
    return entry["finding"], assets, captions


def resolve(root, base, folder, *, components=None):
    import house
    inputs = folder / "inputs"
    revisions.check_files(inputs, base["inputs"])
    req = read_request(revisions.local_path(inputs, base["pack_request"]))
    if components is not None:
        if not set(components).issubset(req["components"]):
            raise ValueError("Requested component is absent from the source issue")
        req["components"] = components
    context_files(root, req)
    if req.get("profile") == "schedule":
        from tools.schedule_data import resolve_schedule
        return resolve_schedule(root, req, base["revision"], inputs)
    if req.get("profile") == "edition":
        from tools.audience_packs import resolve_edition
        return resolve_edition(root, req, base["revision"], inputs)
    if req.get("profile") == "house":
        from tools.house_pack import resolve_house
        return resolve_house(root, req, base["revision"])
    slug = house.identifier(req["room"])
    config = revisions.stored_json(root / "project.json")
    spec = dict(req, issue=base["revision"], house_name=config["name"], slug=slug)
    spec["components"] = [p for p in COMPONENTS if p in req["components"]]
    assets = {}
    if set(spec["components"]) & {"room-review", "drawing"}:
        spec["finding"], assets, spec["view_captions"] = design_evidence(root, inputs, req, slug)
        from house_visuals import Catalogue, checked_placement
        live, frozen = Catalogue(root), Catalogue(root, inputs)
        spec["visual_reviews"] = {}
        for role, path in assets.items():
            view = ("plan" if role == "sheet" else "camera" if role.startswith("camera-") else "photo")
            if role == "sheet":
                view = req.get("sheet_view", "plan")
                if view not in ("plan", "section"):
                    raise ValueError("Choose plan or section for the commissioned drawing")
            phase = req["stage"].split("-")[0] if role == "sheet" else "proposed"
            spec["visual_reviews"][role] = {
                part: checked_placement(live, frozen, path=path, purpose=part, phase=phase, scope="room/"+slug,
                                        view=view, page=req.get("sheet_page", 1) if role == "sheet" else 1)
                for part in spec["components"] if part == "room-review" or (part == "drawing" and role == "sheet")}
    if "shopping" in spec["components"]:
        spec["items"] = shopping_rows(inputs / "shopping.csv", req["room"])
        if spec["items"] != shopping_rows(root / "shopping.csv", req["room"]):
            raise ValueError(f"{req['room']}: shopping selections changed. Begin a fresh issue.")
    spec["sources"] = {role: {"path": path.relative_to(root).as_posix(), "sha256": digest(path)}
                       for role, path in assets.items()}
    return spec, assets


def fingerprint(spec):
    return hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def inspect_pack(root, base, folder):
    from tools.render_pack import check_visual_files, verify
    spec, assets = resolve(root, base, folder)
    envelope = folder / "outputs" / "pack"
    if not envelope.is_dir():
        raise ValueError("Run build-pack for this declared component issue")
    manifest = revisions.stored_json(envelope / "issue-manifest.json")
    if manifest["selection_sha256"] != fingerprint(spec):
        raise ValueError("The selected inputs differ from this build. Begin a fresh issue.")
    if spec.get("profile") == "schedule":
        from tools.schedule_pack import verify_schedule
        return verify_schedule(envelope, spec, manifest)
    if spec.get("profile") == "edition":
        from tools.audience_packs import verify_edition
        return verify_edition(envelope, spec, manifest, assets)
    if spec.get("profile") == "house":
        from tools.house_pack import verify_house
        return verify_house(envelope, spec, manifest)
    checked = verify(envelope, spec, manifest)
    if spec.get("visual_reviews"):
        check_visual_files(envelope / "delivery", spec, assets)
    return checked


def release_check(root, base, stage, draft):
    receipt = draft / "pack-review.json"
    checked = inspect_pack(root, base, stage)
    if not receipt.is_file():
        raise ValueError("Open the extracted issue and record its reader review with check-pack")
    saved = revisions.stored_json(receipt)
    if checked != saved.get("checked"):
        raise ValueError("The issue changed after reader review. Repeat check-pack.")
    return saved


def command(root, revision, action, reviewer=None, finding=None):
    from tools import render_pack
    rev = revisions.revision_id(revision)
    draft = revisions.local_path(root, f"{revisions.WORK}/{rev}")
    saved = revisions.record_dir(root, rev)
    if saved.exists():
        if action != "check-pack" or reviewer or finding:
            raise ValueError("This issue is already saved. Begin a new revision for changes.")
        record = revisions.verify_revision(root, rev)
        if not record.get("pack_issue"):
            raise ValueError("This revision has no component issue receipt")
        return f"Verified issued pack: {saved / 'outputs/pack/delivery/Start here.html'}"
    base = revisions.stored_json(draft / "draft.json")
    if not base.get("pack_request"):
        raise ValueError("Begin the issue with --pack-request and a house-relative request file")
    if action == "plan-pack":
        spec, _ = resolve(root, base, draft)
        if spec.get("profile") in ("house", "edition", "schedule"):
            return "\n".join([spec["purpose"], *spec["files"]])
        return render_pack.plan_text(spec)
    with revisions._save_lock(draft.parent):
        if saved.exists():
            raise ValueError("Issue has already been saved")
        if action == "build-pack":
            target = draft / "outputs" / "pack"
            if not target.exists():
                spec, assets = resolve(root, base, draft)
                with tempfile.TemporaryDirectory(dir=draft.parent, prefix=".staging-") as temp:
                    stage = Path(temp) / "pack"
                    if spec.get("profile") == "house":
                        from tools.house_pack import build_house
                        build_house(stage, spec, assets, fingerprint(spec))
                    elif spec.get("profile") == "schedule":
                        from tools.schedule_pack import build_schedule
                        build_schedule(stage, spec, fingerprint(spec))
                    elif spec.get("profile") == "edition":
                        from tools.audience_packs import build_edition
                        build_edition(stage, spec, assets, fingerprint(spec))
                    else:
                        render_pack.build(stage, spec, assets, fingerprint(spec))
                    revisions.publish_directory(stage, target)
            inspect_pack(root, base, draft)
            return str(target / "delivery/Start here.html")
        checked = inspect_pack(root, base, draft)
        if reviewer is not None or finding is not None:
            if not (reviewer and reviewer.strip() and finding and finding.strip()):
                raise ValueError("Supply both --reviewer and --finding")
            receipt = {"reviewer": reviewer.strip(), "finding": finding.strip(), "checked": checked}
            with tempfile.TemporaryDirectory(dir=draft.parent, prefix=".staging-") as temp:
                staged = Path(temp) / "receipt.json"
                revisions.write_json(staged, receipt)
                os.replace(staged, draft / "pack-review.json")
        return "Verified " + checked["archive"] + " | " + ", ".join(checked["components"])
