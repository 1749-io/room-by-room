"""Review final photos in their room and resolve adjoining rooms for a house issue."""
import csv
import json
import os
import tempfile
import zipfile
from pathlib import Path

from . import house_revisions as revisions
from . import house_openings


def digest(path):
    with path.open("rb") as stream:
        return revisions.transfer(stream)


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Record {label} in the photo review")
    return value


def issued_pairs(room, revision):
    prefix = f"revisions/{revision}/outputs/"
    with (room / "finish-checks.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["revision"] == revision and r["kind"] == "ai-colour"]
    pairs = {}
    for row in rows:
        if row["result"] != "pass" or not all(row[k].startswith(prefix) for k in ("source", "evidence")):
            raise ValueError(f"{room.name}: check the final photograph against this revision's camera")
        name = row["evidence"][len(prefix):]
        if name in pairs:
            raise ValueError(f"Repeated final photo reference: {name}")
        pairs[name] = row["source"][len(prefix):]
    if not pairs:
        raise ValueError(f"{room.name}: no issued photo comparisons")
    return pairs


def window_review(root, outputs, revision, inventory, observations, *, final=False):
    """Check each declared sightline independently of whether the interior is visible."""
    if not isinstance(inventory, dict) or not isinstance(observations, dict) or inventory.keys() != observations.keys():
        raise ValueError("Declare and review every window treatment in this camera, including obscured openings")
    unresolved = []
    for opening, owner in inventory.items():
        required_text(opening, "window or reflected opening")
        room = revisions.local_path(root / "rooms", required_text(owner, "window's room"))
        if room.parent != root / "rooms" or not (room / "review.csv").is_file():
            raise ValueError(f"{opening}: unknown window owner {owner}")
        item = observations[opening]
        if not isinstance(item, dict):
            raise ValueError(f"{opening}: record a window comparison")
        required_text(item.get("comparison"), f"{opening} visual comparison or reason it is hidden")
        visibility = item.get("visibility")
        if visibility in ("outside-frame", "occluded"):
            continue
        if visibility != "visible":
            raise ValueError(f"{opening}: identify window visibility")
        for key in ("treatment", "state", "outside_face"):
            required_text(item.get(key), f"{opening} {key}")
        status = item.get("status")
        if status == "provisional":
            follow_up = required_text(item.get("follow_up"), f"{opening} unresolved detail and owner")
            if "reference" in item or "sha256" in item:
                ref = required_text(item.get("reference"), f"{opening} provisional source")
                source = revisions.local_path(root, ref)
                if not source.is_file() or digest(source) != item.get("sha256"):
                    raise ValueError(f"{opening}: changed or missing provisional source")
            unresolved.append(f"{opening}: provisional window treatment in {owner}. {follow_up}")
            continue
        if status != "matched":
            raise ValueError(f"{opening}: match or disclose the provisional treatment in {owner}")
        source_revision = revisions.revision_id(required_text(item.get("revision"), "source room revision"))
        with (room / "review.csv").open(encoding="utf-8-sig", newline="") as stream:
            current = {r["revision"] for r in csv.DictReader(stream) if r["stage"] == "final-ai" and r["status"] == "pass"}
        if source_revision not in current:
            raise ValueError(f"{opening}: stale window source for {owner}, refresh the visual comparison")
        ref = required_text(item.get("reference"), f"{opening} room reference")
        parts = revisions.safe_relative(ref).parts
        if parts[:3] == ("revisions", source_revision, "outputs"):
            if len(parts) < 4:
                raise ValueError(f"{opening}: identify a room reference file")
            source_outputs = outputs if source_revision == revision else revisions.record_dir(root, source_revision) / "outputs"
            path = revisions.local_path(source_outputs, Path(*parts[3:]).as_posix())
            # Shared room issues store cameras in room folders or register the filenames explicitly.
            if not (source_outputs / owner).is_dir() and any(
                    sibling != room and (source_outputs / sibling.name).is_dir()
                    for sibling in room.parent.iterdir() if sibling.is_dir()):
                pairs = issued_pairs(room, source_revision)
                known = set(pairs) | set(pairs.values())
                if Path(*parts[3:]).as_posix() not in known:
                    raise ValueError(f"{opening}: use the owning room's registered camera or photograph")
            if (source_outputs / owner).is_dir() and parts[3] != owner:
                raise ValueError(f"{opening}: use the owning room's reference")
        elif parts[:2] == ("rooms", owner):
            legacy = revisions.stored_json(root / "project.json").get("legacy_output_revisions", {})
            if source_revision not in legacy.get(owner, []):
                raise ValueError(f"{opening}: link the current saved room revision")
            path = revisions.local_path(root, ref)
        else:
            raise ValueError(f"{opening}: use a reference belonging to {owner} in {source_revision}")
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"{opening}: changed or missing window reference in {owner}")
    if final and unresolved:
        raise ValueError("\n".join(unresolved))
    return unresolved


EXTERIOR_REGISTER = "exterior-views.csv"
EXTERIOR_REVIEW = "exterior-window-review.json"


def exterior_register(root, *, required=False):
    path = root / EXTERIOR_REGISTER
    if not path.is_file():
        if required:
            raise ValueError("Declare current exterior photographs in exterior-views.csv before whole-house issue")
        return {}
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["revision", "photo", "opening", "room"]:
            raise ValueError("Use the exterior-views.csv template columns")
        for row in rows:
            rev = revisions.revision_id(row["revision"])
            name = revisions.safe_relative(row["photo"]).as_posix()
            openings = result.setdefault(rev, {}).setdefault(name, {})
            opening = required_text(row["opening"], "exterior opening")
            if opening in openings:
                raise ValueError(f"{name}: duplicate exterior opening {opening}")
            openings[opening] = required_text(row["room"], "exterior window owner")
    return result


def exterior_review(root, outputs, revision, inventory, *, final=False, unresolved=None):
    """Bind standalone views to a predeclared house register and their reviewed pixels."""
    path = outputs / EXTERIOR_REVIEW
    if not inventory and not path.exists():
        return {}
    if not inventory or not path.is_file():
        raise ValueError(f"{revision}: reconcile exterior-views.csv with {EXTERIOR_REVIEW}")
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict):
        raise ValueError("Expected an exterior photo review object")
    photos = manifest.get("photos")
    if manifest.get("revision") != revision or not isinstance(photos, dict) or photos.keys() != inventory.keys():
        raise ValueError(f"{revision}: review every registered exterior photograph")
    staged = {f"exterior/{revision}/{EXTERIOR_REVIEW}": path}
    holds = []
    for name, openings in inventory.items():
        item = photos[name]
        if not isinstance(item, dict):
            raise ValueError(f"{name}: expected an exterior photo comparison")
        required_text(item.get("reviewer"), "exterior photo reviewer")
        if item.get("openings") != openings:
            raise ValueError(f"{name}: opening inventory or owning room changed since review")
        for key, filename in (("photo", name), ("camera", item.get("camera"))):
            file = revisions.local_path(outputs, required_text(filename, key))
            if not file.is_file() or digest(file) != item.get(key + "_sha256"):
                raise ValueError(f"{name}: changed exterior {key}, repeat the visual review")
            staged[f"exterior/{revision}/{filename}"] = file
        if item["photo_sha256"] == item["camera_sha256"]:
            raise ValueError(f"{name}: use the furnished camera and the finished photograph")
        issues = window_review(root, outputs, revision, openings, item.get("window_treatments"))
        holds.extend(f"{name} / {reason}" for reason in issues)
    if final and holds:
        raise ValueError("\n".join(holds))
    if unresolved is not None:
        unresolved.extend(holds)
    return staged


def review(outputs, room, revision, *, final_windows=False, require_windows=True, require_details=True, require_heads=True,
           shared_doorways=None, require_operation=True):
    """The reviewer judges the images. The gate checks coverage and exact evidence."""
    # Addenda let an existing camera acquire a reviewed brief without editing its issue.
    root = room.parent.parent
    pointer = room / "photo-review-addendum.json"
    documents = outputs
    if pointer.is_file():
        record = revisions.stored_json(pointer)
        if record["source_revision"] == revision:
            supplement = revisions.revision_id(record["revision"])
            documents = revisions.record_dir(root, supplement) / "outputs"
            receipt = revisions.stored_json(documents.parent / "record.json")["outputs"]
            for suffix in (".json", "-brief.json"):
                name = f"photo-reviews/{room.name}{suffix}"
                if digest(revisions.local_path(documents, name)) != receipt.get(name):
                    raise ValueError(f"{room.name}: camera addendum changed after save")
    legacy = revisions.stored_json(root / "project.json").get("legacy_output_revisions", {}) if (root / "project.json").is_file() else {}
    legacy_room = revision in legacy.get(room.name, []) and documents != outputs
    if legacy_room:
        outputs = root
    filename = f"photo-reviews/{room.name}.json"
    if not outputs.is_dir():
        raise ValueError(f"{room.name}: reissue the historic room with a saved photo quality review")
    manifest = revisions.local_path(documents, filename)
    if not manifest.is_file():
        raise ValueError(f"{room.name}: photo quality review missing ({filename})")
    doc = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError("Expected a room photo review object")
    if doc.get("room") != room.name or doc.get("revision") != revision:
        raise ValueError(f"{room.name}: photo quality review is for another room or revision")
    brief = revisions.local_path(documents, f"photo-reviews/{room.name}-brief.json")
    if not brief.is_file():
        raise ValueError(f"{room.name}: record the photographic brief and its required views")
    plan = json.loads(brief.read_text(encoding="utf-8-sig"))
    required_text(plan.get("basis"), "the homeowner or design brief")
    portals = plan.get("openings")
    if not isinstance(portals, dict):
        raise ValueError("Declare the internal openings, glazing and reflected sightlines in the photographic brief")
    outside = set()
    for opening, neighbour in portals.items():
        required_text(opening, "opening or reflection")
        if isinstance(neighbour, dict):
            destination = required_text(neighbour.get("outside_commission"), "uncommissioned room slug")
            path = revisions.local_path(room.parent, destination)
            if path.parent != room.parent or path.exists():
                raise ValueError(f"{opening}: use the registered adjoining room for this opening")
            required_text(neighbour.get("reason"), "reason the uncommissioned room is outside the frame")
            evidence = revisions.local_path(documents, required_text(neighbour.get("reference"), "framing evidence"))
            if (evidence.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
                    or not evidence.is_file() or digest(evidence) != neighbour.get("sha256")):
                raise ValueError(f"{opening}: missing or changed framing evidence for the uncommissioned room")
            outside.add(opening)
            continue
        path = revisions.local_path(room.parent, neighbour)
        if path.parent != room.parent or path == room or not (path / "review.csv").is_file():
            raise ValueError(f"Unknown adjoining room in the photographic brief: {neighbour}")
    required = plan.get("views")
    if not isinstance(required, dict) or "whole-room" not in required or len(required) < 2:
        raise ValueError("Brief the whole room and at least one decision or use to show")
    for key, purpose in required.items():
        required_text(key, "view ID")
        required_text(purpose, "what the view must show")
    if legacy_room:
        with (room / "finish-checks.csv").open(encoding="utf-8-sig", newline="") as stream:
            pairs = {v["evidence"]: v["source"] for v in csv.DictReader(stream)
                     if v["revision"] == revision and v["kind"] == "ai-colour" and v["result"] == "pass"}
        if not pairs or any(not path.startswith(f"rooms/{room.name}/") for pair in pairs.items() for path in pair):
            raise ValueError(f"{room.name}: legacy photo pair must belong to the registered room")
    else:
        pairs = issued_pairs(room, revision)
    seen, covered, final_digests = set(), set(), set()
    photos = doc.get("photos")
    if not isinstance(photos, list):
        raise ValueError("List the reviewed photos")
    for image in photos:
        if not isinstance(image, dict):
            raise ValueError("Expected a photo review entry")
        photo = image.get("photo")
        original = image.get("replaces", image)
        if not isinstance(original, dict) or original.get("photo") not in pairs:
            raise ValueError("Identify the registered photo being reviewed")
        previous = original["photo"]
        if previous in seen or original.get("camera") != pairs[previous]:
            raise ValueError("Match each final photo to its registered furnished camera exactly once")
        seen.add(previous)
        for key in ("camera", "photo"):
            path = revisions.local_path(outputs, image[key])
            if "replaces" in image:
                if documents == outputs or not pointer.is_file():
                    raise ValueError("Save corrected pairs in a separate camera addendum")
                path = revisions.local_path(documents, image[key])
                if not receipt.get(image[key]) or receipt[image[key]] != image.get(key + "_sha256"):
                    raise ValueError("Corrected camera or photo differs from its saved issue")
                if image["camera"] == photo or image["camera_sha256"] == image["photo_sha256"]:
                    raise ValueError("Use the distinct furnished camera and reviewed photograph")
            if digest(path) != image.get(key + "_sha256"):
                raise ValueError(f"Changed {key}: repeat the visual review of {photo}")
        if image["photo_sha256"] in final_digests:
            raise ValueError(f"Repeated final photograph under another filename: {photo}")
        final_digests.add(image["photo_sha256"])
        if image.get("result") != "pass":
            raise ValueError(f"Resolve the photo review for {photo}")
        for key in ("reviewer", "composition", "products_and_operation", "light_and_finish", "architecture", "opening_inspection"):
            required_text(image.get(key), key.replace("_", " "))
        views = image.get("shows")
        if not isinstance(views, list) or not views or any(v not in required for v in views):
            raise ValueError(f"{photo}: identify which briefed views are visible")
        covered.update(views)
        if require_windows:
            window_review(room.parent.parent, outputs, revision, plan.get("windows"),
                          image.get("window_treatments"), final=final_windows)
        neighbours = image.get("visible_rooms")
        if not isinstance(neighbours, list):
            raise ValueError(f"{photo}: inspect openings, glass and reflections and list visible rooms")
        visibility = image.get("openings")
        if not isinstance(visibility, dict) or visibility.keys() != portals.keys() or any(
                state not in ("visible", "occluded", "outside-frame") for state in visibility.values()):
            raise ValueError(f"{photo}: reconcile every opening with the actual camera")
        if any(visibility[key] != "outside-frame" for key in outside):
            raise ValueError(f"{photo}: register and review the adjoining room when its opening enters the frame")
        issues = room / "photo-defects.csv"
        if issues.is_file():
            with issues.open(encoding="utf-8-sig", newline="") as stream:
                for defect in csv.DictReader(stream):
                    if defect["photo_sha256"] == image["photo_sha256"]:
                        raise ValueError(f"Reported photo defect: {defect['finding']}")
        if require_details:
            from .house_photo_details import validate
            validate(plan, image, require_heads=require_heads, require_operation=require_operation)
        expected = {portals[key] for key, state in visibility.items() if state == "visible"}
        found = set()
        for other in neighbours:
            if not isinstance(other, dict):
                raise ValueError("Expected a visible adjoining-room comparison")
            slug = required_text(other.get("room"), "adjoining room")
            folder = revisions.local_path(room.parent, slug)
            if folder.parent != room.parent or folder == room or not (folder / "review.csv").is_file() or slug in found:
                raise ValueError(f"{photo}: unknown, repeated or self-referencing adjoining room {slug}")
            found.add(slug)
            required_text(other.get("through"), "where the adjoining room is seen")
            required_text(other.get("comparison"), "what matches or remains provisional")
            if other.get("status") not in ("matched", "provisional"):
                raise ValueError("Record a matched or provisional adjoining room")
            if other["status"] == "matched":
                for k in ("revision", "reference", "sha256"):
                    required_text(other.get(k), "adjoining room " + k)
                if shared_doorways is not None:
                    for opening, visibility in image["openings"].items():
                        if visibility == "visible" and portals[opening] == slug:
                            connections = plan.get("shared_openings", {})
                            if not isinstance(connections, dict):
                                raise ValueError("Map the shared openings in the photographic brief")
                            shared_doorways[opening] = (slug, connections.get(opening))
        if found != expected:
            raise ValueError(f"{photo}: adjoining rooms differ from visible openings")
    if seen != set(pairs) or covered != set(required):
        raise ValueError(f"{room.name}: incomplete photo coverage. Missing photographs {sorted(set(pairs)-seen)}, views {sorted(set(required)-covered)}")
    return doc


def compare_shared_opening(opening, entry, local, adjoining, sections):
    if not isinstance(entry, dict):
        raise ValueError(f"{opening}: identify the shared opening in the photographic brief")
    if entry.get("kind") in ("fixed-glazing", "open-passage", "reflection"):
        required_text(entry.get("basis"), f"why {opening} has no shared operating door")
        return
    if entry.get("kind") != "doorway" or type(entry.get("mirror_x")) is not bool:
        raise ValueError(f"{opening}: record the shared doorway ID and section orientation")
    doorway = required_text(entry.get("id"), "shared doorway ID")

    def leaves(room, neighbour):
        found = {}
        for section in sections(room).values():
            shared = section[4]
            if shared and shared["id"] == doorway and shared["adjoining_room"] == neighbour:
                leaf = shared["leaf"]
                if leaf in found:
                    raise ValueError(f"{doorway}: repeated shared leaf {leaf} in {room}")
                found[leaf] = section
        return found

    first, second = leaves(local, adjoining), leaves(adjoining, local)
    if not first or first.keys() != second.keys():
        raise ValueError(f"{opening}: identify the same shared leaves in both rooms' native sections")
    for leaf, section in first.items():
        if not house_openings.same_head_section(section, second[leaf], entry["mirror_x"]):
            raise ValueError(f"{opening}: shared doorway sections differ for {leaf}")


def house_issue(root, *, visual_uses=None):
    """Resolve the current registers again immediately before a combined issue."""
    import house
    rooms = sorted((root / "rooms").glob("*/review.csv"))
    if not rooms:
        raise ValueError("The house has no room reviews")
    problems, ready, staged = [], {}, {}
    shared = {}
    for register in rooms:
        room = register.parent
        try:
            rows = house.review_rows(register)
            passed, reason = house.status_through(root, register, rows, "handover")
            if not passed:
                raise ValueError(reason)
            stages = {row["stage"]: row for row in rows}
            revision = stages["handover"]["revision"]
            outputs = revisions.record_dir(root, revision) / "outputs"
            shared[room.name] = {}
            doc = review(outputs, room, revision, final_windows=True, shared_doorways=shared[room.name])
            pack = revisions.local_path(root, stages["handover"]["evidence"])
            if pack.suffix.lower() != ".zip":
                raise ValueError("issue a portable room ZIP")
            ready[room.name] = revision, stages, doc, outputs
            staged[room.name + "/Room-pack.zip"] = pack
            pointer = room / "photo-review-addendum.json"
            if pointer.is_file():
                addendum = revisions.stored_json(pointer)
                if addendum["source_revision"] == revision:
                    supplement = revisions.record_dir(root, addendum["revision"]) / "outputs"
                    for suffix in (".json", "-brief.json"):
                        name = f"photo-reviews/{room.name}{suffix}"
                        staged[f"{room.name}/{name}"] = revisions.local_path(supplement, name)
                    for image in doc["photos"]:
                        if "replaces" in image:
                            for field in ("camera", "photo"):
                                name = image[field]
                                staged[f"{room.name}/corrected/{name}"] = revisions.local_path(supplement, name)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            problems.append(f"{room.name}: {exc}")
    native_heads, verified = {}, {}
    def sections(room):
        if room not in native_heads:
            native_heads[room] = house_openings.shared_head_sections(root, room, ready[room][1], verified)
        return native_heads[room]

    for slug, (_, _, doc, _) in ready.items():
        for opening, (other_room, entry) in shared[slug].items():
            if other_room in ready:
                try:
                    compare_shared_opening(opening, entry, slug, other_room, sections)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    problems.append(f"{slug} / {other_room}: adjoining opening check: {exc}")
        for photo in doc["photos"]:
            for other in photo["visible_rooms"]:
                target = ready.get(other["room"])
                if not target or other["status"] != "matched" or other["revision"] != target[0]:
                    problems.append(f"{slug} / {photo['photo']}: unfinished or stale view into {other['room']}")
                    continue
                refs = {x[k] for x in target[2]["photos"] for k in ("camera","photo")}
                ref = other["reference"]
                candidate = staged.get(f"{other['room']}/corrected/{ref}")
                if candidate is None:
                    candidate = revisions.local_path(target[3], ref)
                if ref not in refs or digest(candidate) != other["sha256"]:
                    problems.append(f"{slug}: adjoining view needs comparison with a current issued camera or photo of {other['room']}")
    for rev, views in exterior_register(root, required=True).items():
        try:
            revisions.verify_revision(root, rev)
            staged.update(exterior_review(root, revisions.record_dir(root, rev) / "outputs", rev, views, final=True))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            problems.append(f"Exterior / {rev}: {exc}")
    if problems:
        raise ValueError("Whole-house photo issue on hold\n" + "\n".join(problems))
    from tools.photo_pack_visuals import photo_uses
    checked = photo_uses(root, ready, staged)
    if visual_uses is not None:
        visual_uses.extend(checked)
    return staged


ARCHIVE = "Whole-house-photo-packs.zip"


def package(root, draft_outputs):
    uses = []
    entries = house_issue(root, visual_uses=uses)
    target = draft_outputs / ARCHIVE
    if target.exists():
        raise ValueError("A house pack already exists here. Begin a fresh revision.")
    with tempfile.TemporaryDirectory(dir=draft_outputs) as folder:
        tmp = Path(folder) / ARCHIVE
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, path in entries.items():
                archive.write(path, name)
            archive.writestr("Visual-uses.json", json.dumps(uses, ensure_ascii=False, sort_keys=True))
        os.link(tmp, target)
    return target


def verify_assembly(root, archive):
    uses = []
    entries = house_issue(root, visual_uses=uses)
    with zipfile.ZipFile(archive) as pack:
        if sorted(pack.namelist()) != sorted([*entries, "Visual-uses.json"]):
            raise ValueError("Whole-house pack differs from the current room inventory")
        if json.loads(pack.read("Visual-uses.json")) != uses:
            raise ValueError("Whole-house photographic placements changed after review")
        for name, path in entries.items():
            with pack.open(name) as stream:
                if revisions.transfer(stream) != digest(path):
                    raise ValueError(f"Whole-house pack contains an older room pack: {name}")
