"""Seating stand-ins. Each has a separate seat and back mesh for the layout read-back helper."""

import math

from . import parts


def dining_chair(root, size, finishes, seat_height_mm):
    """A plain timber side chair with a padded seat and a solid back."""
    width, depth, height = size
    half_w, half_d = width / 2, depth / 2
    pad_top = seat_height_mm / 1000
    seat_top = pad_top - 0.025
    seat_under = seat_top - 0.04
    if not (0.2 < seat_under and pad_top + 0.15 < height):
        raise ValueError("The seat height needs to sit between 265 mm and 150 mm below the top of the back")
    frame, pad = finishes["frame"], finishes["pad"]
    parts.box(root, "seat", -half_w, -half_d, seat_under, half_w, half_d, seat_top, frame, bevel=0.004)
    parts.box(root, "seat pad", -half_w + 0.025, -half_d + 0.025, seat_top, half_w - 0.025, half_d - 0.025, pad_top, pad, bevel=0.008)
    parts.box(root, "back", -half_w, -half_d, seat_top, half_w, -half_d + 0.035, height, frame, bevel=0.004)
    leg = 0.04
    for index, (x, y) in enumerate([(-half_w + 0.015, -half_d + 0.015), (half_w - 0.015 - leg, -half_d + 0.015),
                                    (-half_w + 0.015, half_d - 0.015 - leg), (half_w - 0.015 - leg, half_d - 0.015 - leg)]):
        parts.box(root, f"leg {index + 1}", x, y, 0, x + leg, y + leg, seat_under, frame)


def block_armchair(root, size, finishes, seat_height_mm, arm_height_mm):
    """An upholstered armchair as plain blocks: base, back, two arms, a loose cushion and four feet."""
    width, depth, height = size
    half_w, half_d = width / 2, depth / 2
    seat, arm = seat_height_mm / 1000, arm_height_mm / 1000
    base_top = seat - 0.07
    if not (0.22 <= base_top and seat < arm < height):
        raise ValueError("Use a seat at least 290 mm high, below the arms, and arms below the top of the back")
    cover, cushion, feet = finishes["upholstery"], finishes["cushion"], finishes["feet"]
    arm_w, back_d = width / 6, 0.17
    parts.box(root, "base", -half_w, -half_d, 0.12, half_w, half_d, base_top, cover, bevel=0.015)
    parts.box(root, "back", -half_w, -half_d, base_top, half_w, -half_d + back_d, height, cover, bevel=0.03)
    parts.box(root, "arm, left", -half_w, -half_d + back_d, base_top, -half_w + arm_w, half_d, arm, cover, bevel=0.03)
    parts.box(root, "arm, right", half_w - arm_w, -half_d + back_d, base_top, half_w, half_d, arm, cover, bevel=0.03)
    parts.box(root, "seat", -half_w + arm_w, -half_d + back_d, base_top, half_w - arm_w, half_d - 0.02, seat, cushion, bevel=0.025)
    foot = 0.04
    for index, (x, y) in enumerate([(-half_w + 0.035, -half_d + 0.03), (half_w - 0.035 - foot, -half_d + 0.03),
                                    (-half_w + 0.035, half_d - 0.03 - foot), (half_w - 0.035 - foot, half_d - 0.03 - foot)]):
        parts.box(root, f"foot {index + 1}", x, y, 0, x + foot, y + foot, 0.12, feet)


def rattan_armchair(root, size, finishes, seat_height_mm, arm_height_mm):
    """A rattan tub chair: a hoop that rises from the arms over the back, a cane-woven shell and two loose cushions.

    The shell is a U in plan, straight down each side and round the back, and leans outwards by 7% between the
    seat rail and the hoop. The frame is 34 mm rod, so the overall size follows from the centre lines below.
    """
    width, depth, height = size
    rod, cane, stations = 0.017, 0.0055, 72
    flare, lean, overhang = 0.07, 0.035, 0.057           # hoop wider than the seat, back leaning out, cushion past the front legs
    half = (width / 2 - rod) / (1 + flare)               # half width of the seat rail
    side = (depth - lean - rod - overhang) / (1 + (1 + flare) * 5 / 6)   # straight side, from the back curve's centre to the front
    back_radius = side * 5 / 6
    shift = (back_radius * (1 + flare) + lean + rod - side - overhang) / 2   # centres the footprint on the root
    rail = seat_height_mm / 1000 - 0.135                 # seat rail under a 123 mm cushion
    arm = arm_height_mm / 1000 - rod                     # centre of the hoop at the front of the arms
    crown = height - rod                                 # centre of the hoop at the top of the back
    if not (0.2 <= rail and rail + 0.2 <= arm <= crown - 0.1):
        raise ValueError("Use a seat at least 335 mm high, arms at least 217 mm above the seat rail and a back at least 117 mm above the arms")

    def shell(s, lift):
        """Plan point on the shell from the front left (0), round the back, to the front right (1). lift 0 is the seat rail, 1 the hoop."""
        arc = math.pi * (half + back_radius) / 2
        along = s * (2 * side + arc)
        if along < side:
            x, y = -half, side - along
        elif along < side + arc:
            angle = math.pi * (along - side) / arc
            x, y = -half * math.cos(angle), -back_radius * math.sin(angle)
        else:
            x, y = half, along - side - arc
        grow = 1 + flare * lift
        return x * grow, y * grow - lean * lift * (1.0 if y < 0 else 0.4) + shift

    def hoop_height(s):
        return arm + (crown - arm) * (0.5 - 0.5 * math.cos(2 * math.pi * s)) ** 1.6

    steps = [i / stations for i in range(stations + 1)]
    hoop = [(*shell(s, 1), hoop_height(s)) for s in steps]
    seat_rail = [(*shell(s, 0), rail) for s in steps]
    stretcher = [(x * 0.96, (y - shift) * 0.96 + shift, 0.12) for x, y, _ in seat_rail]
    frame = [(hoop, False), (seat_rail, True)]
    for end in (0, -1):                                  # front legs run on from the arms to the floor
        frame.append((parts.rod_to_floor(hoop[end], (seat_rail[end][0], seat_rail[end][1], 0.0), rod), False))
    for s in (0.36, 0.64):                               # rear legs, raked a little
        x, y = shell(s, 0)
        frame.append((parts.rod_to_floor((x, y, rail), (x * 1.05, (y - shift) * 1.08 - 0.014 + shift, 0.0), rod), False))
    weave = [([(*shell(i / stations, 0), rail), (*shell(i / stations, 0.5), (rail + hoop_height(i / stations)) / 2),
               (*shell(i / stations, 1), hoop_height(i / stations))], False) for i in range(2, stations, 2)]
    weave += [([(*shell(s, band), rail + band * (hoop_height(s) - rail)) for s in steps], False) for band in (0.25, 0.5, 0.75)]
    parts.tubes(root, "frame", frame, rod, finishes["frame"], resolution=6)
    parts.tubes(root, "stretcher", [(stretcher, True)], 0.011, finishes["frame"])
    parts.tubes(root, "cane", weave, cane, finishes["weave"], resolution=2)

    inside = [shell(s, 0) for s in steps][4:-4]
    outline = [(x * 0.90, (y - shift) * 0.90 + 0.01 + shift) for x, y in inside]
    outline += [(half * 0.90, side + overhang + shift), (-half * 0.90, side + overhang + shift)]
    parts.slab(root, "seat", outline, rail + 0.012, rail + 0.135, finishes["cushions"], bevel=0.03)
    cushion_w, cushion_t = half * 0.25 / 0.33, 0.11
    back = parts.slab(root, "back", [(-cushion_w, -cushion_t / 2), (cushion_w, -cushion_t / 2), (cushion_w, cushion_t / 2), (-cushion_w, cushion_t / 2)],
                      0, crown - 0.03 - (rail + 0.13), finishes["cushions"], bevel=0.03)
    back.rotation_euler = (math.radians(8), 0, 0)        # resting against the leaning shell
    back.location = (0, -back_radius + 0.135 + shift, rail + 0.13)
