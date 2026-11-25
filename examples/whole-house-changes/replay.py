"""Replay the fictional house decisions from reopened CAD, tender and programme inputs."""
import argparse
import csv
import json
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parents[1]))


def rectangle(bounds):
    left, bottom, right, top = bounds
    return [[left, bottom], [right, bottom], [right, top], [left, top]]


def pier_results(states):
    from house_routes import analyse

    results = {}
    for revision, parts in states.items():
        fixed = {name: rectangle(parts[name]) for name in ("SouthRun", "EndRun", "Return", "Pier")
                 if name in parts}
        for setting in ("Four", "Eight"):
            dining = parts[setting]
            floor = parts["Floor"].copy()
            # This commission specifies serving up the kitchen side of the occupied table.
            # Clip the study at the table centreline so the solver cannot walk round the far side.
            floor[2] = (dining["Table"][0] + dining["Table"][2]) / 2
            study = {
                "units": "mm", "revision": revision, "basis": "Reopened fictional rear rooms, west serving aisle",
                "floor": rectangle(floor),
                "obstacles": {**fixed, **{name: rectangle(box) for name, box in dining.items()}},
                "journeys": {"serve": {"start": [3430, 0], "end": [3430, 4300],
                                       "width_mm": 825, "uncertainty_mm": 0}},
            }
            serving = analyse(study, "baseline")["serve"]
            results[revision, setting] = {
                "seats": len(dining) - 1,
                "pier_gap": parts.get("Pier", parts["Return"])[0] - parts["EndRun"][2],
                "west_gap": min(box[0] for box in dining.values()) - parts["SouthRun"][2],
                "east_gap": parts["Floor"][2] - max(box[2] for box in dining.values()),
                "tested_mm": serving["tested_mm"], "status": serving["status"],
                "path_mm": serving["path_mm"],
            }
    return results


def quote_results(rows, budget):
    shared = (budget["other_house_packages_including_bathrooms_gbp"]
              + budget["owner_supplied_appliances_gbp"] + budget["protected_reserve_gbp"])
    results = {}
    for builder in ("a", "b"):
        tender = sum(int(row[f"builder_{builder}_gbp"]) for row in rows)
        concept = shared + tender
        occupied = concept + budget["occupied_works_extra_gbp"]
        results[builder] = (tender, concept, occupied, budget["owner_ceiling_gbp"] - occupied)
    return results


def bathroom_nights(plan, nights):
    def available(item, night):
        return all(not start <= night <= end for start, end in plan[item])

    result = []
    for night in range(1, nights + 1):
        usable = []
        if available("common_water", night):
            if available("upstairs_bathroom", night):
                usable.append("upstairs")
            if available("downstairs_shower", night) and available("hall_to_downstairs", night):
                usable.append("downstairs")
        result.append(usable)
    return result


def delayed_handover(plan, first_working_night, wait_for_handover):
    """Give the first room a working night before the second room goes offline."""
    start, end = plan["downstairs_shower"][0]
    new_start = max(start, first_working_night + 1) if wait_for_handover else start
    return {**plan, "upstairs_bathroom": [[1, first_working_night - 1]],
            "downstairs_shower": [[new_start, new_start + end - start]]}


def read_json(name):
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


def print_pier():
    print("CAD revision | diners | pier / occupied west / east gap (mm) | continuous serving route")
    for (revision, _), row in pier_results(read_json("reference/rear-rooms.json")).items():
        print(f"{revision} | {row['seats']} | {row['pier_gap']:.0f} / {row['west_gap']:.0f} / "
              f"{row['east_gap']:.0f} | {row['tested_mm']} mm {row['status']}")


def print_quotes():
    with (FOLDER / "quotes.csv").open(encoding="utf-8", newline="") as stream:
        quotes = quote_results(list(csv.DictReader(stream)), read_json("house-budget.json"))
    print("Builder | comparable package | house total | occupied house total | headroom (GBP)")
    for builder, amounts in quotes.items():
        print(builder.upper(), *amounts, sep=" | ")


def print_bathrooms():
    programme = read_json("programme.json")
    plans = programme["plans"].copy()
    for name, wait in (("late handover, booked demolition", False),
                       ("late handover, dependent demolition", True)):
        plans[name] = delayed_handover(plans["occupied programme"], 7, wait)
    for name, plan in plans.items():
        nights = bathroom_nights(plan, programme["nights"])
        failed = [str(i) for i, rooms in enumerate(nights, 1) if not rooms]
        print(f"{name}: nights without a usable WC and shower: {', '.join(failed) or 'none'}")


if __name__ == "__main__":
    cases = {"pier": print_pier, "quotes": print_quotes, "bathrooms": print_bathrooms}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", choices=["all", *cases], default="all")
    case = parser.parse_args().case
    for name, replay in cases.items():
        if case in ("all", name):
            replay()
