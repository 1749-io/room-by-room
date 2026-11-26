"""Resolve commissioned schedule rows against their captured and current house records."""
import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from graphlib import CycleError, TopologicalSorter
import re

import house
import house_revisions as revisions
from house_delivery import SCHEDULES, digest, fingerprint, required, shopping_rows


def selection(values, what):
    if (not isinstance(values, list) or not values
            or any(not isinstance(v, str) or not v.strip() for v in values)
            or len({v.casefold() for v in values}) != len(values)):
        raise ValueError(f"Select distinct {what}")
    return values


def csv_rows(folder, name):
    path = revisions.local_path(folder, name)
    if not path.is_file():
        raise ValueError(f"Supply the house register {name}")
    fields = {"budget.csv": ("scope", "low_gbp", "high_gbp", "basis", "date", "includes", "exclusions", "decision"),
              "programme.csv": ("task_id", "task", "owner", "predecessors", "duration_days", "not_before",
                                "decision_by", "status", "basis"),
              "decorator-finishes.csv": ("revision", "surface", "manufacturer", "colour", "code", "finish", "status", "evidence")}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        missing = set(fields[path.name]) - set(headers)
        if missing or len(headers) != len(set(headers)):
            raise ValueError(f"{name}: missing or repeated columns, expected {', '.join(fields[path.name])}")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError(f"{name}: unexpected fields on row {reader.line_num}")
            rows.append({key: value or "" for key, value in row.items()})
        return rows


def keyed(rows, key, wanted):
    selected = {}
    for row in rows:
        value = row.get(key, "")
        if wanted == "all" or value in wanted:
            if not value or value in selected:
                raise ValueError(f"Missing or repeated {key}: {value!r}")
            selected[value] = row
    missing = set(wanted) - selected.keys() if wanted != "all" else set()
    if missing or not selected:
        raise ValueError(f"No registered {key} for {sorted(missing) or wanted}")
    return selected


def finish_rows(folder, req):
    rooms = req.get("surfaces")
    if not isinstance(rooms, dict) or not rooms:
        raise ValueError("Name the commissioned rooms, finish revisions and surfaces")
    rows, evidence = [], {}
    seen_rooms = set()
    for name, scope in rooms.items():
        slug = house.identifier(name)
        if slug in seen_rooms or not isinstance(scope, dict):
            raise ValueError(f"Duplicate room or invalid surface scope: {name}")
        seen_rooms.add(slug)
        rev = revisions.revision_id(required(scope, "revision"))
        register = f"rooms/{slug}/decorator-finishes.csv"
        data = csv_rows(folder, register)
        surfaces = selection(scope.get("surfaces"), "commissioned surfaces")
        current = {r["surface"].strip().casefold(): r for r in data}
        for surface in surfaces:
            message = house.check_decorator(folder, folder / "rooms" / slug, rev, surface)
            if message:
                raise ValueError(f"{name}, {surface}: {message}")
            r = current[surface.strip().casefold()]
            if r["revision"] != rev:
                raise ValueError(f"{name}, {surface}: the latest recorded finish is {r['revision']}")
            path = r["evidence"]
            if revisions.safe_relative(path).parts[0] == revisions.WORK:
                raise ValueError("Link a saved finish instruction or sample decision")
            evidence[path] = digest(revisions.local_path(folder, path))
            rows.append({"Room": name, "Surface": r["surface"], "Manufacturer": r["manufacturer"],
                         "Colour": r["colour"], "Code": r["code"], "Finish": r["finish"],
                         "Status": r["status"], "Approval reference": r.get("decision_ref") or rev + " / " + r["surface"],
                         "Finish revision": rev})
    return rows, evidence


def budget_source(folder, req):
    limits = req.get("budget_lines")
    if (not isinstance(limits, dict) or not limits or
            any(not isinstance(s, str) or not s.strip() for s in limits.values())):
        raise ValueError("Assign each commissioned budget scope to Base, Excluded or a named option")
    return keyed(csv_rows(folder, "budget.csv"), "scope", limits)


def money(value, field):
    if not value:
        return None
    try:
        number = Decimal(value)
        if not number.is_finite() or number != number.quantize(Decimal(".01")):
            raise ValueError
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Expected a GBP amount to the penny for {field}: {value}") from error
    return number


def cost_rows(folder, req):
    source = budget_source(folder, req)
    rows, references, seen, scenarios = [], {}, set(), {}
    for scope, scenario in req["budget_lines"].items():
        if scenario != scenario.strip() or scenarios.setdefault(scenario.casefold(), scenario) != scenario:
            raise ValueError(f"Inconsistent scenario name: {scenario}")
        if scenario.casefold() in ("base", "excluded") and scenario not in ("Base", "Excluded"):
            raise ValueError("Use Base or Excluded for the reserved scenario names")
        r = source[scope]
        lo, hi = (money(r.get(f), scope) for f in ("low_gbp", "high_gbp"))
        if lo is not None and hi is not None and hi < lo:
            raise ValueError(f"{scope}: high price is below low price")
        pricing = "Priced"
        if lo is None or hi is None:
            pricing = "Open" if lo is None and hi is None else "Check range"
        ids = (r.get("shopping_ids") or "").split()
        if ids:
            room = required(r, "room")
            items = {item["Item ID"]: item for item in shopping_rows(folder / "shopping.csv", room)}
            amount = Decimal("0")
            for item_id in ids:
                if item_id in seen or item_id not in items or not items[item_id]["Quantity x unit GBP"]:
                    raise ValueError(f"{scope}: duplicated, missing or unallocated shopping item {item_id}")
                seen.add(item_id)
                references[item_id] = fingerprint(items[item_id])
                amount += Decimal(items[item_id]["Quantity x unit GBP"])
            if amount != lo or amount != hi:
                raise ValueError(f"{scope}: linked shopping lines total GBP {amount:.2f}")
        rows.append({"Scope": scope, "Scenario": scenario, "Room": r.get("room", ""), "Trade": r.get("trade", ""),
                     "Phase": r.get("phase", ""), "Cost type": r.get("cost_type", ""),
                     "Low GBP": str(lo) if lo is not None else "", "High GBP": str(hi) if hi is not None else "",
                     "Pricing": pricing, "VAT basis": r.get("vat_basis") or "Unconfirmed",
                     "Price date": r.get("date") or "Unconfirmed", "Basis": required(r, "basis"),
                     "Includes": r.get("includes", ""), "Exclusions": r.get("exclusions", ""),
                     "Decision": r.get("decision", ""), "Shopping IDs": " ".join(ids)})
    return rows, references


def iso(value, field):
    try:
        day = date.fromisoformat(value)
        if str(day) != value or day.year < 1901:
            raise ValueError
        return day
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field}: use a calendar date in YYYY-MM-DD format") from error


def programme_rows(folder, req):
    start = iso(required(req, "start_date"), "Programme start")
    wanted = req.get("tasks")
    if wanted != "all":
        selection(wanted, "programme task IDs or use all")
    source = keyed(csv_rows(folder, "programme.csv"), "task_id", wanted)
    deps = {key: (r.get("predecessors") or "").split() for key, r in source.items()}
    for key, predecessors in deps.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", key):
            raise ValueError(f"Use a stable alphanumeric task ID: {key}")
        missing = set(predecessors) - source.keys()
        if missing or len(set(predecessors)) != len(predecessors):
            raise ValueError(f"{key}: missing or repeated predecessor {predecessors}")
    if len({key.casefold() for key in source}) != len(source):
        raise ValueError("Task IDs must also be distinct in a spreadsheet")
    try:
        order = tuple(TopologicalSorter(deps).static_order())
    except CycleError as error:
        raise ValueError(f"Programme dependency cycle: {error.args[-1]}") from error
    rows, finishes = [], {}
    for key in order:
        r = source[key]
        days = r.get("duration_days", "")
        if days and not re.fullmatch(r"[0-9]{1,5}", days):
            raise ValueError(f"{key}: use whole calendar days, including zero for a milestone")
        earliest = iso(r["not_before"], key) if r.get("not_before") else start
        first = last = None
        if all(finishes[d] is not None for d in deps[key]):
            try:
                first = max([start, earliest, *(finishes[d] + timedelta(days=1) for d in deps[key])])
                if days:
                    last = first + timedelta(days=max(0, int(days)-1))
            except OverflowError as error:
                raise ValueError(f"{key}: forecast is outside the supported calendar") from error
        finishes[key] = last
        deadline = iso(r["decision_by"], key) if r.get("decision_by") else None
        rows.append({"Task ID": key, "Task": required(r, "task"), "Phase": r.get("phase", ""),
                     "Owner": required(r, "owner"), "Predecessors": " ".join(deps[key]), "Days": int(days) if days else "",
                     "Not before": r.get("not_before", ""), "Forecast start": str(first or ""), "Forecast finish": str(last or ""),
                     "Decision by": str(deadline) if deadline else "",
                     "Timing": ("Awaiting duration" if last is None else "Late" if last > deadline else "Within date") if deadline else "",
                     "Status": required(r, "status"), "Occupancy and services": r.get("occupancy_and_services", ""),
                     "Payment milestone": r.get("payment_milestone", ""), "Basis": required(r, "basis")})
    return rows, {}


def inputs_for(root, req):
    kind, = req["components"]
    if kind == "decorator-finishes":
        _, approvals = finish_rows(root, req)
        names = [f"rooms/{house.identifier(name)}/decorator-finishes.csv" for name in req["surfaces"]]
        return list(dict.fromkeys([*names, *approvals]))
    if kind == "cost-schedule":
        includes_shopping = any(r.get("shopping_ids") for r in budget_source(root, req).values())
        return ["budget.csv", "shopping.csv"] if includes_shopping else ["budget.csv"]
    return ["programme.csv"]


def schedule_paths(req, issue):
    kind, = req["components"]
    prefix = f"Schedules/{kind}"
    stem = f"{prefix}/{req['house']}-{kind}-{issue}"
    return prefix + "/Read me.html", stem + ".xlsx", stem + ".csv"


def resolve_schedule(root, req, issue, inputs):
    kind, = req["components"]
    reader = {"decorator-finishes": finish_rows, "cost-schedule": cost_rows, "programme": programme_rows}[kind]
    rows, evidence = reader(inputs, req)
    if (rows, evidence) != reader(root, req):
        raise ValueError(f"{SCHEDULES[kind]}: selected rows or approval evidence changed. Begin a fresh issue.")
    index, workbook, csv_path = schedule_paths(req, issue)
    files = {"Start here.html": "Issue contents", index: SCHEDULES[kind],
             workbook: "Open the editable workbook", csv_path: "Download the issued rows"}
    sources = {"selected rows": {"sha256": fingerprint(rows)}}
    sources.update({key: {"sha256": value} for key, value in evidence.items()})
    spec = dict(req, house_name=revisions.stored_json(root / "project.json")["name"], issue=issue, slug=kind,
                room="Commissioned surfaces" if kind == "decorator-finishes" else "House schedule",
                rows=rows, files=files, sources=sources)
    return spec, {}
