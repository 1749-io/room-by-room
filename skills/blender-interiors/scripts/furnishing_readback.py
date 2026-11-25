"""Compare a room's product quantities with tagged objects in a live Blender scene."""

from collections import Counter


def visible_collections(layer):
    """Return render-enabled collections in the active view layer."""
    if layer.exclude or layer.collection.hide_render:
        return set()
    collections = {layer.collection}
    for child in layer.children:
        collections.update(visible_collections(child))
    return collections


def check_furnishings(scene, layer, room_id, expected):
    """Tag one representative mesh per purchasing unit, including one per pair sold together."""
    if not room_id or any(type(qty) is not int or qty < 0 for qty in expected.values()):
        raise ValueError(
            "Supply a room ID and non-negative whole purchasing quantities"
        )
    collections = visible_collections(layer.layer_collection)
    found = Counter()
    objects = {}
    for obj in scene.objects:
        if obj.get("furnishing_room") != room_id:
            continue
        ref = obj.get("shopping_ref")
        if not ref:
            raise ValueError(
                f"{obj.name} is tagged for the room without a shopping reference"
            )
        if obj.hide_render or not collections.intersection(obj.users_collection):
            continue
        found[ref] += 1
        objects.setdefault(ref, []).append(obj.name)
    discrepancies = {
        ref: {"expected": expected.get(ref, 0), "observed": found[ref]}
        for ref in sorted(set(expected) | set(found))
        if expected.get(ref, 0) != found[ref]
    }
    return {"objects": objects, "discrepancies": discrepancies}
