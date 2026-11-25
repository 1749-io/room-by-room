"""Read the completed solves and compare with a simply supported Euler-Bernoulli beam."""

import json
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

root = Path(sys.argv[1])
case = json.loads((root / "case.json").read_text(encoding="utf-8-sig"))
L, b, h, E, q = [
    case[k] for k in ("span_mm", "width_mm", "depth_mm", "E_MPa", "line_load_N_per_mm")
]
I = b * h**3 / 12
ref = q * L / 2
elastic_defl = 5 * q * L**4 / (384 * E * I)
M = q * L**2 / 8
stress = M * h / (2 * I)
frame = json.loads((root / "pynite-results.json").read_text())


def fields(path):
    groups = {"DISP": {}, "STRESS": {}}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith(" -4"):
            current = groups.get(line.split()[1])
        elif line.startswith(" -3"):
            current = None
        elif current is not None and line.startswith(" -1"):
            current[int(line[3:13])] = [
                float(line[n : n + 12]) for n in range(13, len(line.rstrip()), 12)
            ]
    return groups


def reactions(path):
    values = re.findall(
        r"total force.*?for set (LEFT|RIGHT)[^\n]*\n\s*([-+.\dE]+)\s+([-+.\dE]+)\s+([-+.\dE]+)",
        path.read_text(),
    )
    assert {row[0] for row in values} == {"LEFT", "RIGHT"}
    return {row[0]: float(row[3]) for row in values}


def read_mesh(label, nx, ny, nz):
    folder = root / "calculix" / label
    data = fields(folder / "opening.frd")
    rx = reactions(folder / "opening.dat")

    def node(i, j, k):
        return 1 + k + (nz + 1) * (j + (ny + 1) * i)

    axis = [data["DISP"][node(i, ny // 2, nz // 2)][2] for i in range(nx + 1)]
    sx = np.array(
        [
            [
                [data["STRESS"][node(i, j, k)][0] for k in range(nz + 1)]
                for j in range(ny + 1)
            ]
            for i in range(nx + 1)
        ]
    )
    assert len(data["DISP"]) == (nx + 1) * (ny + 1) * (nz + 1)
    record = {
        "nodes": len(data["DISP"]),
        "elements": nx * ny * nz,
        "down_mm": -axis[nx // 2],
        "left_N": rx["LEFT"],
        "right_N": rx["RIGHT"],
        "mid_top_Sxx_MPa": sx[nx // 2, ny // 2, nz],
        "mid_bottom_Sxx_MPa": sx[nx // 2, ny // 2, 0],
    }
    assert abs(rx["LEFT"] - ref) < 0.1 and abs(rx["RIGHT"] - ref) < 0.1
    assert abs(1 + axis[nx // 2] / elastic_defl) < 0.02 and axis[nx // 2] < 0
    assert abs(axis[0]) < 1e-6 and abs(axis[-1]) < 1e-6
    assert np.allclose(axis, axis[::-1], atol=2e-5)
    assert sx[nx // 2, ny // 2, 0] > 0 and sx[nx // 2, ny // 2, nz] < 0
    return record, axis, sx


results = {}
for label, (nx, ny, nz) in case["meshes_xyz"].items():
    results[label], axis, sx = read_mesh(label, nx, ny, nz)
    if label == "fine":
        fine_axis = np.asarray(axis)
        fine_sxx = sx[:, ny // 2, :].T
        x = np.linspace(0, L, nx + 1)
        z = np.linspace(-h / 2, h / 2, nz + 1)
assert abs(frame["left_N"] - ref) < 1e-6 and abs(frame["right_N"] - ref) < 1e-6
assert abs(frame["vertical_mm"][24] + elastic_defl) < 1e-8
assert abs(frame["mid_moment_Nmm"] - M) < 1e-6
assert abs(1 - results["coarse"]["down_mm"] / results["fine"]["down_mm"]) < 0.005
assert abs(1 - results["fine"]["mid_bottom_Sxx_MPa"] / stress) < 0.02
assert abs(1 + results["fine"]["mid_top_Sxx_MPa"] / stress) < 0.02
summary = {
    "case": case["title"],
    "hand": {
        "reaction_each_N": ref,
        "mid_deflection_mm": elastic_defl,
        "mid_moment_Nmm": M,
        "outer_fibre_stress_MPa": stress,
    },
    "pynite": {
        "version": frame["version"],
        "left_N": frame["left_N"],
        "right_N": frame["right_N"],
        "mid_deflection_mm": -frame["vertical_mm"][24],
        "mid_moment_Nmm": frame["mid_moment_Nmm"],
    },
    "calculix": results,
    "coarse_to_fine_deflection_percent": 100
    * abs(results["fine"]["down_mm"] - results["coarse"]["down_mm"])
    / results["fine"]["down_mm"],
}
(root / "verified-results.json").write_text(json.dumps(summary, indent=2) + "\n")


plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": "#283E42",
        "text.color": "#20383D",
    }
)
fig, axes = plt.subplots(
    2,
    1,
    figsize=(9.2, 6.1),
    layout="constrained",
    gridspec_kw={"height_ratios": [1.3, 1]},
)
fig.suptitle(
    "Fictional kitchen opening under a uniform load", fontsize=17, fontweight="bold"
)
ax = axes[0]
ax.set_title(
    "Vertical displacement along the centreline",
    loc="left",
    fontsize=11,
    fontweight="bold",
)
ax.plot(
    x / 1000,
    fine_axis,
    color="#1C7773",
    linewidth=2.5,
    label="CalculiX solid, fine mesh",
)
ax.scatter(
    np.array(frame["x_mm"])[::4] / 1000,
    frame["vertical_mm"][::4],
    s=29,
    facecolors="white",
    edgecolors="#9A481C",
    linewidth=1.6,
    zorder=3,
    label="PyNite beam",
)
ax.set(
    xlim=(-0.025, 3.025),
    ylim=(-1.08, 0.08),
    xlabel="Position along span (m)",
    ylabel="Vertical movement (mm)",
)
ax.grid(axis="y", alpha=0.22)
ax.legend(loc="lower left", ncols=1, fontsize=8, framealpha=0.93)
ax = axes[1]
ax.set_title(
    "CalculiX longitudinal stress through the beam at mid-width",
    loc="left",
    fontsize=11,
    fontweight="bold",
)
im = ax.pcolormesh(
    x / 1000,
    z,
    fine_sxx,
    shading="gouraud",
    cmap="RdBu_r",
    norm=TwoSlopeNorm(vcenter=0, vmin=-6, vmax=6),
)
ax.set(
    xlabel="Position along span (m)",
    ylabel="Depth coordinate (mm)",
    yticks=[-60, 0, 60],
)
cb = fig.colorbar(im, ax=ax, pad=0.02)
cb.set_label("Stress (MPa)")
fig.savefig(root / "solver-comparison.png", dpi=160, facecolor="white")
