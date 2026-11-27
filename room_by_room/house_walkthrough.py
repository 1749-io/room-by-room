"""Check occupied journeys and operating space on the fully dressed camera scene."""
import networkx as nx

from room_by_room.house_routes import analyse, footprint, point


def check(camera, cad):
    study = camera.get("walkthrough")
    if not isinstance(study, dict):
        return "export the fully dressed scene walkthrough after placing the last item"
    stops = study["stops"]
    expected = cad.get("walkthrough_stops")
    if not isinstance(expected, dict) or not expected or not isinstance(stops, dict):
        return "inventory the seats, access points and operating positions in CAD and the furnished scene"
    kinds = {name: stop["kind"] for name, stop in stops.items()}
    if any(kinds.get(name) != kind for name, kind in expected.items()):
        return "furnished walkthrough omits or changes a CAD walkthrough stop"
    if "access" not in kinds.values() or set(kinds.values()) - {"seat", "access", "operating", "activity"}:
        return "identify each walkthrough stop and at least one room access point"

    inventory = study["scene_objects"]
    if (not isinstance(inventory, list) or not all(isinstance(name, str) and name.strip() for name in inventory)
            or len(inventory) != len(set(inventory))):
        return "export distinct physical object IDs from the fully dressed scene"
    exclusions = study.get("exclusions", {})
    if not isinstance(exclusions, dict) or not all(isinstance(reason, str) and reason.strip() for reason in exclusions.values()):
        return "explain each object excluded from the occupied walkthrough"
    covered = set(study["obstacles"])
    conflicts = (covered & set(exclusions)) | (set(inventory) ^ (covered | set(exclusions)))
    if conflicts:
        return "reconcile the scene object inventory and walkthrough footprints: " + ", ".join(sorted(conflicts))
    obstacles = {name: footprint(outline, name) for name, outline in study["obstacles"].items()}
    floor = footprint(study["floor"], "floor")
    for name, stop in stops.items():
        position = point(stop["point"])
        if stop["kind"] in {"seat", "operating"}:
            owner = stop["object"]
            if owner not in obstacles:
                return f"{name}: include the native furniture footprint"
            space = footprint(stop["use_space"], name)
            if space.geom_type != "Polygon" or not space.intersects(obstacles[owner]):
                return f"{name}: connect the full use space to the native furniture footprint"
            if not space.covers(position) or not floor.covers(space):
                return f"{name}: check the standing position and full use space inside the room"
            for item, solid in obstacles.items():
                if item != owner and space.intersection(solid).area > 0:
                    return f"{name}: {item} obstructs the space needed to use {owner}"

    graph = nx.Graph()
    graph.add_nodes_from(stops)
    journeys = {}
    for name, route in study["journeys"].items():
        origin, destination = route["from"], route["to"]
        graph.add_edge(origin, destination)
        journeys[name] = dict(route, start=stops[origin]["point"], end=stops[destination]["point"])
    if not journeys or not nx.is_connected(graph):
        return "connect every walkthrough stop to the room access network"
    results = analyse(dict(study, revision=camera["revision"], units=camera["units"],
                           basis=camera["basis"], journeys=journeys), "baseline")
    for name, result in results.items():
        if result["status"] != "fits":
            return (f"{name}: {result['status']}, {result['tested_mm']} mm modelled against "
                    f"{result['required_mm']} mm required. Review the fully dressed route")
    return None
