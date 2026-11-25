"""Optional illustration from reopened box geometry and the same route calculation as replay.py."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

from replay import pier_results, read_json


def draw(output):
    states = read_json("reference/rear-rooms.json")
    results = pier_results(states)
    colours = {"fixed": "#8ba99b", "return": "#b8b8b2", "pier": "#b95436",
               "table": "#cfac76", "seat": "#667e91"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.3), layout="constrained")
    for ax, revision, title in zip(axes, ("R1", "R2", "R3"),
                                   ("Finished pier added", "Shorter unit, table shifted", "Prep bench moved")):
        parts = states[revision]
        result = results[revision, "Eight"]
        for name, bounds in {**parts, **parts["Eight"]}.items():
            if name in ("Four", "Eight"):
                continue
            left, bottom, right, top = bounds
            category = {"SouthRun": "fixed", "EndRun": "fixed", "Return": "return",
                        "Pier": "pier", "Table": "table"}.get(name, "seat")
            colour = "#fbf8f2" if name == "Floor" else colours[category]
            ax.add_patch(Rectangle((left, bottom), right-left, top-bottom,
                                   facecolor=colour, edgecolor="#454947", linewidth=0.8))
        route = result["path_mm"]
        ax.plot(*zip(*route), color="#205576", linewidth=2.1, linestyle="--")
        ax.text(3430, -330, "From hall", ha="center", fontsize=9)
        ax.text(3430, 4500, "To utility", ha="center", fontsize=9)
        ax.text(1200, 2820, "End unit", ha="center", fontsize=9)
        ax.text(1460, parts["SouthRun"][1] + 650, "Prep bench", ha="center", fontsize=9)
        ax.text(5100, 1450, "Table", ha="center", fontsize=9)
        ax.set_title(f"{revision}   {title}\n{result['tested_mm']} mm continuous route", fontsize=12)
        ax.set_aspect("equal")
        ax.set_xlim(-60, 7470)
        ax.set_ylim(-760, 5070)
        ax.axis("off")
    fig.suptitle("Serving past eight diners", fontsize=19, fontweight="bold")
    fig.legend(handles=[Patch(color=colours[k], label=v) for k, v in
                        (("pier", "Finished pier"), ("return", "Retained return"),
                         ("seat", "Occupied seat"))], loc="outside lower center", ncol=3)
    with output.open("xb") as stream:
        fig.savefig(stream, format=output.suffix.lstrip(".") or "png", dpi=145, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    draw(parser.parse_args().output)
