"""Validate the reviewer's architectural comparisons against the briefed inventory."""
import math


def region(check, name):
    box = check.get(name)
    if not isinstance(box, list) or len(box) != 4 or any(
        type(n) not in (int, float) or not 0 <= n <= 1 for n in box
    ) or box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError(f"Mark a non-empty normalised {name} region around the detail")


def review_head(item, check):
    head = check.get("head_review")
    if not isinstance(head, dict) or not isinstance(head.get("finding"), str) or not head["finding"].strip():
        raise ValueError(f"{item}: inspect the top of the opening independently of the leaf")
    state = head.get("expected")
    if state not in ("closed above", "glazed overlight", "intentional opening", "mixed"):
        raise ValueError(f"{item}: identify the intended treatment above the opening")
    for view in ("camera", "photo"):
        observed = head.get(view + "_state")
        if observed == "outside-frame" or observed == "occluded":
            reason = head.get(view + "_reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"{item}: explain why the head cannot be inspected in the {view}")
        elif observed != state:
            raise ValueError(f"{item}: visible door head in the {view} differs from the design")
        else:
            region(head, view)


def review_operation(plan, item, check):
    intended = plan.get("opening_operations", {}).get(item)
    if intended not in {"hinged", "sliding", "folding", "pivot", "fixed", "open passage", "other"}:
        raise ValueError(f"{item}: identify the selected opening mechanism in the photo brief")
    if check.get("camera_operation") != intended or check.get("photo_operation") != intended:
        raise ValueError(f"{item}: the camera and photo must show the selected opening mechanism")
    if check.get("occupied_access") != "clear" or not str(check.get("use_finding") or "").strip():
        raise ValueError(f"{item}: resolve or verify the visible access to the seats and through route")


def validate(plan, image, *, require_heads=True, require_operation=True):
    inventory = plan.get("architectural_details")
    results = image.get("architectural_details")
    if not isinstance(inventory, dict) or set(inventory) != {"wall_mounts", "openings"}:
        raise ValueError("Inventory wall-mounted items near openings and the opening assemblies")
    if not isinstance(results, dict) or set(results) != set(inventory):
        raise ValueError("Review both architectural detail inventories for this photo")
    for category, items in inventory.items():
        observations = results[category]
        if not isinstance(items, list) or not all(isinstance(i, str) and i.strip() for i in items):
            raise ValueError("Name each architectural detail in the brief")
        if len(set(items)) != len(items) or not isinstance(observations, dict) or set(items) != set(observations):
            raise ValueError(f"Review every declared detail in {category}")
        if category == "openings" and not set(plan["openings"]).issubset(items):
            raise ValueError("Include each briefed internal opening in the detail inventory")
        for item, check in observations.items():
            if not isinstance(check, dict) or not isinstance(check.get("finding"), str) or not check["finding"].strip():
                raise ValueError(f"{item}: record the visual finding")
            visibility = check.get("visibility")
            declared = image["openings"].get(item) if category == "openings" else None
            if declared and declared != visibility:
                raise ValueError(f"{item}: visibility differs from the opening review")
            if visibility in ("outside-frame", "occluded"):
                continue
            if visibility != "visible" or check.get("result") != "pass":
                raise ValueError(f"{item}: resolve the visible architectural detail before issue")
            region(check, "camera")
            region(check, "photo")
            if category == "wall_mounts":
                gap = check.get("model_clearance_mm")
                if type(gap) not in (int, float) or not math.isfinite(gap) or gap <= 0:
                    raise ValueError(f"{item}: measure positive clearance to trim and the moving leaf")
                if check.get("photo_clear_of_opening") is not True:
                    raise ValueError(f"{item}: frame crosses or obscures the opening in the photo")
            else:
                if require_operation:
                    review_operation(plan, item, check)
                if require_heads:
                    review_head(item, check)
                for key in ("model_leaves", "photo_leaves"):
                    leaves = check.get(key)
                    if not isinstance(leaves, list) or not all(isinstance(v, str) and v.strip() for v in leaves):
                        raise ValueError(f"{item}: identify each leaf or fixed panel in order")
                if check["model_leaves"] != check["photo_leaves"] or check.get("continuous_frame_and_hardware") is not True:
                    raise ValueError(f"{item}: reconcile leaves, framing, hardware and opening state")
