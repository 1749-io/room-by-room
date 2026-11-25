"""Generate both meshes and solve the frame member for a fictional opening."""

import json
import sys
from importlib.metadata import version
from pathlib import Path

from Pynite import FEModel3D

ROOT = Path(sys.argv[1])
case = json.loads((ROOT / "case.json").read_text(encoding="utf-8-sig"))
L, b, h = (case[key] for key in ("span_mm", "width_mm", "depth_mm"))
E, nu, q = (case[key] for key in ("E_MPa", "poisson", "line_load_N_per_mm"))
I = b * h**3 / 12
model = FEModel3D()
model.add_node("Left", 0, 0, 0)
model.add_node("Right", L, 0, 0)
model.add_material("Fictional elastic material", E, E / (2 * (1 + nu)), nu, 0)
# Rectangular St Venant torsion constant. The vertical test induces no torsion.
J = h * b**3 * (1 / 3 - 0.21 * b / h * (1 - b**4 / (12 * h**4)))
model.add_section("Test rectangle", b * h, I, h * b**3 / 12, J)
model.add_member(
    "Head", "Left", "Right", "Fictional elastic material", "Test rectangle"
)
model.def_support("Left", True, True, True, True, False, False)
model.def_support("Right", False, True, True, False, False, False)
model.add_member_dist_load("Head", "FZ", -q, -q, case="Test")
model.add_load_combo("Assumed", {"Test": 1})
model.analyze_linear(check_statics=True)
m = model.members["Head"]
stations = [L * i / 48 for i in range(49)]
moment = abs(m.moment("My", L / 2, "Assumed"))
out = {
    "version": version("PyNiteFEA"),
    "x_mm": stations,
    "vertical_mm": [float(m.deflection("dz", x, "Assumed")) for x in stations],
    "moment_Nmm": [float(m.moment("My", x, "Assumed")) for x in stations],
    "left_N": float(model.nodes["Left"].RxnFZ["Assumed"]),
    "right_N": float(model.nodes["Right"].RxnFZ["Assumed"]),
    "mid_moment_Nmm": float(moment),
    "mid_bending_stress_MPa": float(moment * h / (2 * I)),
}
(ROOT / "pynite-results.json").write_text(json.dumps(out, indent=2))
print(
    "PyNite",
    out["version"],
    out["left_N"],
    out["right_N"],
    out["vertical_mm"][24],
    moment,
)


def make_mesh(label, nx, ny, nz):
    folder = ROOT / "calculix" / label
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["*HEADING", "Fictional opening solver benchmark, N and mm", "*NODE"]

    def node(i, j, k):
        return 1 + k + (nz + 1) * (j + (ny + 1) * i)

    def element(i, j, k):
        return 1 + k + nz * (j + ny * i)

    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                xyz = (L * i / nx, b * (j / ny - 0.5), h * (k / nz - 0.5))
                lines.append(f"{node(i, j, k)}, " + ", ".join(f"{x:.8f}" for x in xyz))
    lines.append("*ELEMENT,TYPE=C3D8I,ELSET=SOLID")
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                corners = [
                    node(i + di, j + dj, k + dk)
                    for dk in (0, 1)
                    for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1))
                ]
                lines.append(", ".join(str(x) for x in [element(i, j, k)] + corners))
    for name, i in (("LEFT", 0), ("RIGHT", nx)):
        lines.extend(
            [
                f"*NSET,NSET={name}",
                ", ".join(str(node(i, j, nz // 2)) for j in range(ny + 1)),
            ]
        )
    lines.extend(
        [
            "*MATERIAL,NAME=TEST",
            "*ELASTIC",
            f"{E}, {nu}",
            "*SOLID SECTION,ELSET=SOLID,MATERIAL=TEST",
            "*BOUNDARY",
            "LEFT,1,1",
            "LEFT,3,3",
            "RIGHT,3,3",
            f"{node(0, ny // 2, nz // 2)},2,2",
            f"{node(nx, ny // 2, nz // 2)},2,2",
            "*STEP",
            "*STATIC",
            "*DLOAD",
        ]
    )
    for i in range(nx):
        for j in range(ny):
            lines.append(f"{element(i, j, nz - 1)}, P2, {q / b:.10f}")
    lines.extend(
        [
            "*NODE FILE",
            "U",
            "*EL FILE",
            "S",
            "*NODE PRINT,NSET=LEFT,TOTALS=ONLY",
            "RF",
            "*NODE PRINT,NSET=RIGHT,TOTALS=ONLY",
            "RF",
            "*END STEP",
        ]
    )
    (folder / "opening.inp").write_text("\n".join(lines) + "\n", encoding="ascii")


for label, counts in case["meshes_xyz"].items():
    make_mesh(label, *counts)
