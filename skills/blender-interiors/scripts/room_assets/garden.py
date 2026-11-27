"""Garden context seen through glazing. These show height and mass. They are not a planting design."""

from . import parts

# Canopy masses in units of the main mass's plan radius and of the tree's height:
# plan offset x, plan offset y, plan radius, centre height, half height.
CANOPY = [(0.0, 0.0, 1.0, 0.70, 0.30), (0.55, 0.30, 0.80, 0.52, 0.24), (-0.50, -0.35, 0.75, 0.56, 0.225)]
SPAN_X = (min(x - r for x, _, r, _, _ in CANOPY), max(x + r for x, _, r, _, _ in CANOPY))
SPAN_Y = (min(y - r for _, y, r, _, _ in CANOPY), max(y + r for _, y, r, _, _ in CANOPY))


def tree(root, size, finishes):
    """A trunk under three rounded canopy masses. The root is the foot of the trunk.

    The height is exact, for a surveyed or LiDAR height. The canopy fills the stated spread, which lies a
    little off-centre from the trunk, and the returned extent says where.
    """
    spread_x, spread_y, height = size
    unit_x = spread_x / (SPAN_X[1] - SPAN_X[0])
    unit_y = spread_y / (SPAN_Y[1] - SPAN_Y[0])
    trunk = max(0.12, height * 0.018)
    if trunk > min(unit_x, unit_y):
        raise ValueError("The canopy is too narrow to cover the trunk")
    parts.cylinder(root, "trunk", 0, 0, 0, height * 0.45, trunk, finishes["trunk"], segments=16)
    for index, (x, y, radius, centre, half) in enumerate(CANOPY):
        parts.ellipsoid(root, f"canopy {index + 1}", (x * unit_x, y * unit_y, centre * height),
                        (radius * unit_x, radius * unit_y, half * height), finishes["canopy"])
    return [SPAN_X[0] * unit_x, SPAN_Y[0] * unit_y, 0.0, SPAN_X[1] * unit_x, SPAN_Y[1] * unit_y, height]


def hedge(root, size, finishes):
    """A clipped hedge as one softened block. The length runs along X."""
    length, thickness, height = size
    parts.box(root, "hedge", -length / 2, -thickness / 2, 0, length / 2, thickness / 2, height, finishes["foliage"],
              bevel=min(0.08, thickness / 4))
