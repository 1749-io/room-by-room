"""Table and storage stand-ins."""

from . import parts


def dining_table(root, size, finishes, top_thickness_mm, leg_mm, leg_inset_mm):
    """A rectangular table: a top on four square legs set in from the corners."""
    width, depth, height = size
    half_w, half_d = width / 2, depth / 2
    top, leg, inset = top_thickness_mm / 1000, leg_mm / 1000, leg_inset_mm / 1000
    if not (0 < top < height and 2 * (inset + leg) < min(width, depth)):
        raise ValueError("The top and the four legs do not fit inside the requested size")
    parts.box(root, "top", -half_w, -half_d, height - top, half_w, half_d, height, finishes["top"], bevel=0.004)
    for index, (x, y) in enumerate([(-half_w + inset, -half_d + inset), (half_w - inset - leg, -half_d + inset),
                                    (-half_w + inset, half_d - inset - leg), (half_w - inset - leg, half_d - inset - leg)]):
        parts.box(root, f"leg {index + 1}", x, y, 0, x + leg, y + leg, height - top, finishes["legs"])


def sideboard(root, size, finishes, leg_height_mm):
    """A long low cabinet on two sledge legs. The front faces +Y and the back stands against a wall."""
    width, depth, height = size
    half_w, half_d = width / 2, depth / 2
    lift = leg_height_mm / 1000
    if not 0 < lift < height - 0.2:
        raise ValueError("Leave at least 200 mm of cabinet above the legs")
    parts.box(root, "carcass", -half_w, -half_d, lift, half_w, half_d, height, finishes["carcass"], bevel=0.004)
    for index, x in enumerate([-half_w + 0.06, half_w - 0.10]):
        parts.box(root, f"leg {index + 1}", x, -half_d + 0.06, 0, x + 0.04, half_d - 0.06, lift, finishes["legs"])


def side_table(root, size, finishes, top_thickness_mm):
    """A round occasional table: a disc top on a slim stem and a small floor plate."""
    width, depth, height = size
    if abs(width - depth) > 1e-6:
        raise ValueError("A round table needs the same width and depth")
    radius, top = width / 2, top_thickness_mm / 1000
    parts.cylinder(root, "top", 0, 0, height - top, height, radius, finishes["top"])
    parts.cylinder(root, "stem", 0, 0, 0.012, height - top, 0.025, finishes["stem"])
    parts.cylinder(root, "floor plate", 0, 0, 0, 0.012, radius * 0.6, finishes["stem"])
