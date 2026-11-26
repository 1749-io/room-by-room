"""Planar household journeys, using millimetres from a reviewed CAD export."""
import math

import networkx as nx
import shapely
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import nearest_points, unary_union


def number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number in millimetres")
    return value


def footprint(value, name):
    try:
        geom = shape(value) if isinstance(value, dict) else Polygon(value)
    except (ValueError, TypeError, KeyError, shapely.errors.ShapelyError) as exc:
        raise ValueError(f"Invalid polygon for {name}") from exc
    if (geom.geom_type not in {"Polygon", "MultiPolygon"} or geom.is_empty
            or not geom.is_valid or geom.has_z or geom.area <= 0):
        raise ValueError(f"{name} needs a valid, non-empty 2D footprint")
    return geom


def point(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("Each route endpoint needs two plan coordinates")
    return Point(*(number(v, "Coordinate") for v in value))


def corridor(free, start, end, width):
    # Compensate for chord approximation at rounded corners. An inscribed
    # eight-segment quadrant must clear the full radius between vertices.
    radius = width / (2 * math.cos(math.pi / 32))
    inset = free.buffer(-radius, quad_segs=8) if width else free
    for region in shapely.get_parts(inset):
        if region.geom_type == "Polygon" and region.covers(start) and region.covers(end):
            return region
    return None


def connected_path(region, start, end):
    """Join triangles through shared edges and straighten the resulting walk."""
    a, b = start.coords[0], end.coords[0]
    if region.covers(LineString([a, b])):
        return LineString([a, b])
    graph = nx.Graph()
    for triangle in shapely.constrained_delaunay_triangles(region).geoms:
        corners = list(triangle.exterior.coords)
        nodes = [((x + u) / 2, (y + v) / 2) for (x, y), (u, v) in zip(corners, corners[1:])]
        for endpoint in (start, end):
            if triangle.covers(endpoint):
                nodes.append(endpoint.coords[0])
        for i, p in enumerate(nodes):
            for q in nodes[i + 1:]:
                graph.add_edge(p, q, weight=math.dist(p, q))
    try:
        walk = nx.shortest_path(graph, a, b, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        raise ValueError("Check the mesh connection at the route endpoints") from exc
    kept = [walk[0]]
    for i in range(2, len(walk)):
        if not region.covers(LineString([kept[-1], walk[i]])):
            kept.append(walk[i - 1])
    line = LineString([*kept, walk[-1]])
    if not region.covers(line):
        raise ValueError("Route geometry needs review at a mesh boundary")
    return line


def reposition(geom, change, centre):
    delta = point(change.get("translate_mm", [0, 0]))
    turned = rotate(geom, number(change.get("rotate_deg", 0), "Rotation"), origin=centre)
    return translate(turned, delta.x, delta.y)


def measure(floor, obstacles, journey, movements):
    width = number(journey["width_mm"], "Required width")
    uncertainty = number(journey["uncertainty_mm"], "Overall width uncertainty")
    if width <= 0 or uncertainty < 0:
        raise ValueError("A journey needs positive width and non-negative uncertainty")
    start, end = point(journey["start"]), point(journey["end"])
    if start.equals(end):
        raise ValueError("The start and destination must be distinct")
    if not floor.covers(start) or not floor.covers(end):
        raise ValueError("A journey endpoint lies outside the exported floor")
    barriers = dict(obstacles)
    for name, value in journey.get("in_use", {}).items():
        if name in barriers:
            raise ValueError(f"Duplicate occupied envelope: {name}")
        if isinstance(value, dict) and "attached_to" in value:
            parent = value["attached_to"]
            if parent not in obstacles or (parent in movements and movements[parent] is None):
                raise ValueError(f"Re-export the occupied envelope for {parent}")
            envelope = footprint(value["outline"], name)
            if parent in movements:
                change, centre = movements[parent]
                envelope = reposition(envelope, change, centre)
            barriers[name] = envelope
        else:
            barriers[name] = footprint(value, name)
    free = floor.difference(unary_union(list(barriers.values())))
    result = {"status": "restricted", "required_mm": width, "uncertainty_mm": uncertainty,
              "tested_mm": 0, "path_mm": [], "measurements": journey.get("measurements", [])}
    if not isinstance(result["measurements"], list) or not all(
            isinstance(m, str) and m.strip() for m in result["measurements"]):
        raise ValueError("Outstanding measurements must be a list of named checks")
    if corridor(free, start, end, 0) is None:
        result["finding"] = "Disconnected in the modelled use state"
        if result["measurements"] or uncertainty:
            result["status"] = "measure"
        return result

    low = 0
    high = math.ceil(2 * min(start.distance(free.boundary), end.distance(free.boundary))) + 1
    while high - low > 1:
        mid = (low + high) // 2
        if corridor(free, start, end, mid) is None:
            high = mid
        else:
            low = mid
    result["tested_mm"] = low
    comfortable = corridor(free, start, end, width + uncertainty)
    borderline = corridor(free, start, end, max(0, width - uncertainty))
    if result["measurements"] or (comfortable is None and borderline is not None):
        result["status"] = "measure"
    elif comfortable is not None:
        result["status"] = "fits"
    region = comfortable if comfortable is not None else corridor(free, start, end, low)
    path = connected_path(region, start, end)
    boundaries = {"floor edge": floor.boundary, **{n: p.boundary for n, p in barriers.items()}}
    name = min(boundaries, key=lambda n: path.distance(boundaries[n]))
    pinch, _ = nearest_points(path, boundaries[name])
    actual = path.distance(free.boundary) * 2
    if actual + 1e-5 < (width + uncertainty if comfortable is not None else low):
        raise ValueError("The continuous route falls below its tested clearance")
    result.update(path_mm=list(path.coords), length_mm=round(path.length),
                  pinch_mm=list(pinch.coords[0]), beside=name, path_clearance_mm=math.floor(actual + 1e-6),
                  finding="Continuous route checked against the occupied plan")
    return result


def analyse(study, option):
    if study["units"] != "mm" or not study["revision"] or not study["basis"].strip():
        raise ValueError("Supply the revision, modelling assumptions and plan geometry in mm")
    floor = footprint(study["floor"], "floor")
    obstacles = {n: footprint(v, n) for n, v in study["obstacles"].items() if v is not None}
    if "floor edge" in study["obstacles"]:
        raise ValueError("Reserve the name 'floor edge' for the floor boundary")
    allowed = study.get("allowed_changes", {})
    if not isinstance(allowed, dict) or any(
            n not in study["obstacles"] or mode not in ("reposition", "alter") for n, mode in allowed.items()):
        raise ValueError("Name each permitted object and its reposition or alter permission")
    options = study.get("options", {})
    movements = {}
    if "baseline" in options:
        raise ValueError("The baseline is the unmodified reference layout")
    if option != "baseline":
        if option not in options:
            raise ValueError(f"Unknown route option: {option}")
        changed = options[option]
        if not changed or set(changed) - set(allowed):
            raise ValueError(f"Option {option} is outside the recorded scope")
        for name, change in changed.items():
            if allowed[name] == "reposition":
                if (not isinstance(change, dict) or not change or name not in obstacles
                        or change.keys() - {"translate_mm", "rotate_deg"}):
                    raise ValueError(f"Only rigid repositioning is authorised for {name}")
                movements[name] = (change, obstacles[name].centroid)
                obstacles[name] = reposition(obstacles[name], *movements[name])
            elif change is None:
                obstacles.pop(name, None)
                movements[name] = None
            else:
                obstacles[name] = footprint(change, name)
                movements[name] = None
        for name, movement in movements.items():
            if movement is None:
                continue
            moved = obstacles[name]
            if not floor.covers(moved):
                raise ValueError(f"{name} would leave the modelled floor")
            for other, solid in obstacles.items():
                if other != name and moved.intersection(solid).area > 1e-6:
                    raise ValueError(f"{name} would overlap {other}")
    journeys = study["journeys"]
    if not isinstance(journeys, dict) or not journeys:
        raise ValueError("Declare at least one named household journey")
    return {name: measure(floor, obstacles, spec, movements) for name, spec in journeys.items()}
