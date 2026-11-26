"""Check opening and installation clearances against local fixed projections."""
import json
import math

import house_revisions as revisions


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

    doors = spec["door_heads"]
    if not isinstance(doors, dict):
        raise ValueError("Inventory the architectural doors visible or operating in this space")
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
        intent[name] = (reference, door["design_sha256"], door["field_mm"], door["expected"])
    return intent


def review(folder, room, revision, *, camera=False, cad_folder=None, cad_revision=None, heads_only=False):
    """Read only the named snapshot or draft. A problem returns a descriptive gate hold."""
    try:
        suffix = ".camera.json" if camera else ".json"
        path = revisions.local_path(folder, f"outputs/openings/{room}{suffix}")
        if not path.is_file():
            return f"missing {'furnished scene' if camera else 'CAD'} opening clearance review for {room} at {revision}"
        spec = json.loads(path.read_text(encoding="utf-8-sig"))
        if (spec["revision"] != revision or spec["room"] != room or spec["units"] != "mm"
                or not isinstance(spec["basis"], str) or not spec["basis"].strip()):
            return "opening clearance revision, room, millimetres and evidence basis must match"
        model = spec["model"]
        if not model.startswith(("inputs/", "outputs/")):
            return "link the reopened model inside this revision's inputs or outputs"
        source = revisions.local_path(folder, model)
        expected = {".blend"} if camera else {".fcstd", ".ifc", ".step", ".stp"}
        if source.suffix.lower() not in expected or not source.is_file():
            return "opening clearance source model is missing"
        with source.open("rb") as stream:
            if revisions.transfer(stream) != spec["model_sha256"]:
                return "source model changed since the opening clearance read-back"
        heads = door_heads(spec, (cad_folder or folder) if camera else folder)
        if camera:
            cad_folder = cad_folder or folder
            if spec.get("cad_revision") != (cad_revision or revision):
                return "furnished opening study must name its CAD revision"
            cad_path = revisions.local_path(cad_folder, f"outputs/openings/{room}.json")
            if not cad_path.is_file():
                return "missing matching CAD opening inventory for the furnished scene"
            cad = json.loads(cad_path.read_text(encoding="utf-8-sig"))
            if heads != door_heads(cad, cad_folder):
                return "Reconcile the CAD and Blender door inventory, dimensions and intended head sections"
            if not heads_only and interfaces(spec["zones"]) != interfaces(cad["zones"]):
                return "CAD and furnished scene cover different opening interfaces. Reconcile the projections and full travel"
            cad_problem = review(cad_folder, room, cad_revision or revision, heads_only=heads_only)
        else:
            cad_problem = None
        if heads_only:
            return cad_problem
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
            return cad_problem
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
        return "; ".join(issues) or cad_problem
    except ImportError:
        return "install the route dependencies for 3D clearance checks"
    except (KeyError, TypeError, AttributeError, OSError, ValueError, OverflowError) as exc:
        return f"invalid opening clearance evidence: {exc}"
