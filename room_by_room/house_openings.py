"""Check opening and installation clearances against local fixed projections."""
import json
import math

from . import house_revisions as revisions


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Use finite dimensions in millimetres")
    return value


def names(values):
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("List the native geometry IDs for both sides of each interface")
    if len(set(values)) != len(values):
        raise ValueError("Duplicate geometry ID within one inventory")
    return values


def inventory(zone):
    body = names(zone["installed"])
    moving = names(zone["sweeps"])
    if set(body).intersection(moving):
        raise ValueError("Use separate installed and full-travel envelopes")
    return body + moving, names(zone["obstacles"])


def interfaces(zones):
    result = set()
    for zone in zones:
        parts, obstacles = inventory(zone)
        for part in parts:
            role = "installed" if part in zone["installed"] else "sweep"
            result.update((role, part, obstacle) for obstacle in obstacles)
    return result


def geometry(data, name):
    from shapely.geometry import Polygon
    if name not in data:
        raise ValueError(f"Missing geometry for {name}. Measure it or keep the interface on hold")
    item = data[name]
    xy = [(number(x), number(y)) for x, y in item["xy"]]
    low, high = map(number, item["z"])
    poly = Polygon(xy)
    if poly.is_empty or not poly.is_valid or poly.area <= 0 or high <= low:
        raise ValueError(f"Invalid solid envelope for {name}")
    return poly, low, high


def door_heads(spec, design_folder):
    """Compare native elevation cuts with the intended assembly above each shut leaf."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    doors = spec.get("door_heads")
    if not isinstance(doors, dict):
        raise ValueError("Record door_heads from the reopened model for every architectural door visible or operating here")
    if not doors and not (isinstance(spec.get("no_doors_reason"), str) and spec["no_doors_reason"].strip()):
        raise ValueError("Explain the scope of a door-free inventory")
    intent = {}
    for name, door in doors.items():
        basis = door["basis"]
        if not isinstance(name, str) or not name.strip() or not isinstance(basis, str) or not basis.strip():
            raise ValueError("Identify the door and the source for its head treatment")
        reference = door["design_reference"]
        if not reference.startswith(("inputs/", "outputs/")):
            raise ValueError(f"{name}: link the intended door detail in the CAD revision")
        with revisions.local_path(design_folder, reference).open("rb") as stream:
            if revisions.transfer(stream) != door["design_sha256"]:
                raise ValueError(f"{name}: intended door detail changed since review")
        width, height = map(number, door["field_mm"])
        if min(width, height) <= 0:
            raise ValueError(f"{name}: measure the elevation from the shut leaf top to the partition top")
        field = box(0, 0, width, height)
        layers = {}
        for side in ("expected", "observed"):
            solids = {}
            for piece in door[side]:
                role = piece["role"]
                if role not in ("opaque", "glazing", "open") or not isinstance(piece["id"], str) or not piece["id"].strip():
                    raise ValueError(f"{name}: identify each band of wall, frame, glazing or intentional air")
                poly = Polygon([(number(x), number(z)) for x, z in piece["xz"]])
                if not poly.is_valid or poly.area <= 0 or not field.covers(poly):
                    raise ValueError(f"{name}: invalid {side} door-head section")
                solids.setdefault(role, []).append(poly)
            layers[side] = {role: unary_union(parts) for role, parts in solids.items()}
            regions = list(layers[side].values())
            if not unary_union(regions).covers(field):
                raise ValueError(f"{name}: {side} section leaves an unexplained gap above the leaf")
            if any(a.intersection(b).area > 0 for i, a in enumerate(regions) for b in regions[i+1:]):
                raise ValueError(f"{name}: overlapping material and void in the {side} section")
        if (layers["expected"].keys() != layers["observed"].keys()
                or any(not poly.equals(layers["observed"][role]) for role, poly in layers["expected"].items())):
            raise ValueError(f"{name}: modelled wall, glazing or air above the door differs from the design")
        shared = door.get("shared_opening")
        if shared is not None and (not isinstance(shared, dict) or
                any(not isinstance(shared.get(k), str) or not shared[k].strip()
                    for k in ("id", "leaf", "adjoining_room"))):
            raise ValueError(f"{name}: identify the shared doorway, leaf and adjoining room")
        intent[name] = (reference, door["design_sha256"], door["field_mm"], door["expected"], shared)
    return intent


def registered_opening_folder(root, room, revision, verified):
    """Resolve the current geometry with the frozen receipts for a saved correction."""
    folder = revisions.record_dir(root, revision)
    pointer = revisions.local_path(root, f"rooms/{room}/opening-review-addendum.json")
    if not pointer.is_file():
        return folder
    active = revisions.stored_json(pointer)
    if revisions.revision_id(active["source_revision"]) != revision:
        return folder

    def receipt(key):
        if key not in verified:
            verified[key] = revisions.verify_revision(root, key)
        return verified[key]

    binder = revisions.revision_id(active["revision"])
    saved = receipt(binder)
    name = f"opening-addenda/{room}.json"
    if name not in saved["outputs"]:
        raise ValueError(f"Missing saved opening addendum for {room}")
    binding = revisions.stored_json(revisions.record_dir(root, binder) / "outputs" / name)
    if (binding["source_revision"] != revision or binding["room"] != room
            or not isinstance(binding["reviewer"], str) or not binding["reviewer"].strip()):
        raise ValueError("Opening addendum must match the source revision, room and reviewer")
    study = revisions.revision_id(binding["study_revision"])
    if study == revision:
        raise ValueError("An opening correction requires a separate saved study")
    for key in (revision, study):
        outputs = receipt(key)["outputs"]
        for suffix in (".json", ".camera.json"):
            report = f"openings/{room}{suffix}"
            frozen = f"revisions/{key}/outputs/{report}"
            if report not in outputs or saved["inputs"].get(frozen) != outputs[report]:
                raise ValueError(f"Missing or stale opening study binding: {frozen}")
    return revisions.record_dir(root, study)


def registered_review(root, room, revision, *, camera=False, heads_only=False, verified=None, walkthrough=False):
    """Apply a saved room addendum only to the registered source revision it reviewed."""
    folder = revisions.record_dir(root, revision)
    try:
        current = registered_opening_folder(root, room, revision, {} if verified is None else verified)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return f"invalid saved opening addendum: {exc}"
    return review(folder, room, revision, camera=camera, heads_only=heads_only,
                  correction=current if current != folder else None, walkthrough=walkthrough)


def shared_head_sections(root, room, stages, verified):
    """Read the current saved sections for the two registered native handovers."""
    heads = []
    for camera, stage in ((False, "proposed-cad"), (True, "blender")):
        revision = stages[stage]["revision"]
        folder = registered_opening_folder(root, room, revision, verified)
        if folder.name not in verified:
            verified[folder.name] = revisions.verify_revision(root, folder.name)
        suffix = ".camera.json" if camera else ".json"
        if f"openings/{room}{suffix}" not in verified[folder.name]["outputs"]:
            raise ValueError(f"{room}: shared doorway needs its saved {stage} opening report")
        spec = native_study(folder, room, folder.name, camera)
        if not camera:
            cad_folder = folder
        elif spec.get("cad_revision") != cad_folder.name:
            raise ValueError(f"{room}: furnished doorway section uses a different CAD revision")
        heads.append(door_heads(spec, cad_folder))
    if heads[0] != heads[1]:
        raise ValueError(f"{room}: reconcile the shared doorway in CAD and the furnished model")
    return heads[0]


def same_head_section(left, right, mirror_x):
    """Compare like sections from the leaf top, independent of labels and model-floor datums."""
    from shapely.affinity import scale
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    if left[2] != right[2]:
        return False
    def regions(pieces):
        shapes = {}
        for piece in pieces:
            shapes.setdefault(piece["role"], []).append(Polygon(piece["xz"]))
        return {role: unary_union(parts) for role, parts in shapes.items()}
    first, second = regions(left[3]), regions(right[3])
    if mirror_x:
        origin = (left[2][0] / 2, 0)
        second = {role: scale(shape, xfact=-1, origin=origin) for role, shape in second.items()}
    return first.keys() == second.keys() and all(shape.equals(second[role]) for role, shape in first.items())


def native_study(folder, room, revision, camera):
    suffix = ".camera.json" if camera else ".json"
    path = revisions.local_path(folder, f"outputs/openings/{room}{suffix}")
    if not path.is_file():
        raise ValueError(f"missing {'furnished scene' if camera else 'CAD'} opening clearance review for {room} at {revision}")
    spec = json.loads(path.read_text(encoding="utf-8-sig"))
    if (spec["revision"] != revision or spec["room"] != room or spec["units"] != "mm"
            or not isinstance(spec["basis"], str) or not spec["basis"].strip()):
        raise ValueError("opening clearance revision, room, millimetres and evidence basis must match")
    model = spec["model"]
    if not model.startswith(("inputs/", "outputs/")):
        raise ValueError("link the reopened model inside this revision's inputs or outputs")
    source = revisions.local_path(folder, model)
    expected = {".blend"} if camera else {".fcstd", ".ifc", ".step", ".stp"}
    if source.suffix.lower() not in expected or not source.is_file():
        raise ValueError("opening clearance source model is missing")
    with source.open("rb") as stream:
        if revisions.transfer(stream) != spec["model_sha256"]:
            raise ValueError("source model changed since the opening clearance read-back")
    return spec


def movement_problem(spec):
    zones = spec["zones"]
    if not isinstance(zones, list):
        return "supply a list of operating areas"
    solids = spec.get("geometry", {})
    if not isinstance(solids, dict):
        return "supply named solid envelopes for the opening review"
    if not zones:
        reason = spec.get("no_interfaces_reason")
        if not isinstance(reason, str) or not reason.strip():
            return "inventory opening interfaces or explain why none apply"
        if solids:
            return "unassessed opening geometry in a review declaring no interfaces"
        return None
    issues = []
    used = set()
    for zone in zones:
        title = zone["name"]
        if not isinstance(title, str) or not title.strip() or not isinstance(zone["travel"], str) or not zone["travel"].strip():
            return "name the operating area and the full movement tested"
        required = number(zone["required_mm"])
        uncertainty = zone["uncertainty_mm"]
        if required < 0 or (uncertainty is not None and number(uncertainty) < 0):
            return "opening allowance and uncertainty must be non-negative"
        parts, fixed = inventory(zone)
        if set(parts).intersection(fixed):
            return "a moving assembly and its obstacles must use distinct IDs"
        parsed = {key: geometry(solids, key) for key in parts + fixed}
        used.update(parsed)
        for part in parts:
            envelope, low, high = parsed[part]
            for obstacle in fixed:
                projection, bottom, top = parsed[obstacle]
                gap = math.hypot(envelope.distance(projection), max(low-top, bottom-high, 0))
                if gap <= 0 or (uncertainty is not None and (gap <= uncertainty or gap - uncertainty < required)):
                    issues.append(f"{title}: {part} / {obstacle}, {gap:.1f} mm modelled clearance")
        if uncertainty is None:
            issues.append(f"{title}: site or product uncertainty still to measure")
    if set(solids) - used:
        issues.append("unassessed opening geometry: " + ", ".join(sorted(set(solids) - used)))
    return "; ".join(issues) or None


def reviewed_study(folder, room, revision, camera, design_folder, correction, heads_only):
    source = native_study(folder, room, revision, camera)
    if correction is None:
        return source, door_heads(source, design_folder)
    updated = native_study(correction, room, correction.name, camera)
    if camera and (source.get("cad_revision") != revision or updated.get("cad_revision") != correction.name):
        raise ValueError("Furnished opening studies must name their respective CAD revisions")
    heads = door_heads(updated, correction)
    if set(source.get("door_heads", {})) - heads.keys():
        raise ValueError("Corrected inventory omits a previously reviewed door")
    if heads_only:
        return source, heads
    if updated.get("zones") is None and source["model_sha256"] == updated["model_sha256"]:
        return source, heads
    if not isinstance(updated.get("zones"), list):
        raise ValueError(f"Door heads checked at {correction.name}. Remeasure full travel on the changed "
                         f"{'furnished scene' if camera else 'CAD model'} before room handover")
    problem = movement_problem(source)
    if problem:
        raise ValueError(f"Registered movement hold: {problem}")
    if interfaces(source["zones"]) - interfaces(updated["zones"]):
        raise ValueError("Corrected model is missing a registered opening interface")
    return updated, heads


def review(folder, room, revision, *, camera=False, cad_folder=None, cad_revision=None, heads_only=False,
           correction=None, walkthrough=False):
    """Check the measured sections and, for a full handover, operating clearances."""
    try:
        cad_folder = cad_folder or folder
        cad_revision = cad_revision or revision
        spec, heads = reviewed_study(folder, room, revision, camera, cad_folder, correction, heads_only)
        if camera:
            expected_cad = correction.name if correction and spec["revision"] == correction.name else cad_revision
            if spec.get("cad_revision") != expected_cad:
                return "furnished opening study must name its CAD revision"
            cad, cad_heads = reviewed_study(cad_folder, room, cad_revision, False, cad_folder, correction, heads_only)
            if heads != cad_heads:
                return "Reconcile the CAD and Blender door inventory, dimensions and intended head sections"
            if not heads_only:
                if interfaces(spec["zones"]) != interfaces(cad["zones"]):
                    return "CAD and furnished scene cover different opening interfaces. Reconcile the projections and full travel"
                problem = movement_problem(cad)
                if problem:
                    return problem
        if heads_only:
            return None
        problem = movement_problem(spec)
        if camera and walkthrough and not problem:
            from room_by_room.house_walkthrough import check
            return check(spec, cad)
        return problem
    except ImportError:
        return "install the route dependencies for 3D clearance checks"
    except (KeyError, TypeError, AttributeError, OSError, ValueError, OverflowError) as exc:
        return f"invalid opening clearance evidence: {exc}"
