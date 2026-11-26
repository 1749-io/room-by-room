"""Publish and check the editable, portable and offline versions of a schedule."""
import io
import math
from datetime import date, datetime
from decimal import Decimal
from html import escape
from pathlib import Path
from urllib.parse import quote

import openpyxl
from openpyxl.utils import get_column_letter
from xlsxwriter.utility import xl_col_to_name

from room_by_room.house_delivery import SCHEDULES
from tools import render_pack
from tools.check_delivery import Page
from tools.schedule_data import schedule_paths

HEADER = 5                         # zero-based table header row
DATES = {"Not before", "Forecast start", "Forecast finish", "Decision by"}
AMOUNTS = {"Low GBP", "High GBP"}
TABS = {"decorator-finishes": "Finishes", "cost-schedule": "Cost lines", "programme": "Programme"}
TOTAL_COLUMNS = ("Scenario", "Known low GBP", "Known high GBP", "Open or invalid lines", "Total low GBP", "Total high GBP")


def totals(rows):
    scenarios = dict.fromkeys(["Base", *(r["Scenario"] for r in rows if r["Scenario"] != "Excluded")])
    result = []
    for scenario in scenarios:
        chosen = [r for r in rows if r["Scenario"] in ("Base", scenario)]
        known = [r for r in chosen if r["Pricing"] == "Priced"]
        low, high = [float(sum(Decimal(r[k]) for r in known)) for k in ("Low GBP", "High GBP")]
        gaps = len(chosen)-len(known)
        result.append([scenario, low, high, gaps, "" if gaps else low, "" if gaps else high])
    return result


def workbook_rows(spec):
    rows = spec["rows"]
    if spec["slug"] != "programme":
        return rows
    slots = max(2, max(len(r["Predecessors"].split()) for r in rows))
    result = []
    for row in rows:
        cells = {}
        for label, value in row.items():
            if label == "Predecessors":
                ids = value.split()
                cells.update({f"After {i+1}": ids[i] if i < len(ids) else "" for i in range(slots)})
            else:
                cells[label] = value
        result.append(cells)
    return result


def serial(value):
    return (date.fromisoformat(value) - date(1899, 12, 30)).days


def native(label, value):
    if value == "":
        return ""
    if label in AMOUNTS:
        return float(value)
    return serial(value) if label in DATES else value


def formulae(kind, labels, row):
    cells = {name: xl_col_to_name(col) + str(row) for col, name in enumerate(labels)}
    if kind == "cost-schedule":
        lo, hi = cells["Low GBP"], cells["High GBP"]
        group = cells["Scenario"]
        valid = f'OR({group}="Excluded",SUMPRODUCT(--(CostScenarios={group}))=1)'
        return {"Pricing": f'=IF(NOT({valid}),"Check scenario",IF(COUNTA({lo}:{hi})=0,"Open",'
                           f'IF(AND(COUNT({lo}:{hi})=2,{hi}>={lo}),"Priced","Check range")))'}
    if kind != "programme":
        return {}
    ids, dates = xl_col_to_name(labels.index("Task ID")), xl_col_to_name(labels.index("Forecast finish"))
    first = HEADER + 2
    bounds = ["$B$4", cells["Not before"]]
    pending = []
    for name, cell in cells.items():
        if name.startswith("After "):
            prior = (f'INDEX(${dates}${first}:${dates}{row-1},MATCH({cell},${ids}${first}:${ids}{row-1},0))'
                     if row > first else "NA()")
            bounds.append(f'IF({cell}="",0,{prior}+1)')
            pending.append(f'IF({cell}="",FALSE,COUNT({prior})=0)')
    start, end, days, deadline = (cells[key] for key in ("Forecast start", "Forecast finish", "Days", "Decision by"))
    return {"Forecast start": '=IF(OR(' + ",".join(pending) + '),"",MAX(' + ",".join(bounds) + "))",
            "Forecast finish": f'=IF(OR({days}="",{start}=""),"",IF(AND(ISNUMBER({days}),{days}>=0,'
                               f'INT({days})={days}),{start}+MAX(0,{days}-1),NA()))',
            "Timing": f'=IF({deadline}="","",IF({end}="","Awaiting duration",IF({end}>{deadline},"Late","Within date")))'}


def summary_formula(row):
    def aggregate(column, condition):
        def term(scenario):
            return f'SUMPRODUCT(--(CostLines[Scenario]={scenario}),--(CostLines[Pricing]{condition}){column})'
        return "=" + term(f"A{row}") + (f'+{term("$A$7")}' if row != 7 else "")
    return [aggregate(",CostLines[Low GBP]", '="Priced"'), aggregate(",CostLines[High GBP]", '="Priced"'),
            aggregate("", '<>"Priced"') + '+COUNTIF(CostLines[Pricing],"Check scenario")',
            f'=IF(D{row}=0,B{row},"")', f'=IF(D{row}=0,C{row},"")']


def banner(sheet, spec, title, book):
    sheet.hide_gridlines(2)
    title_style = book.add_format({"font_size": 18, "bold": True, "font_color": "#234F43", "valign": "vcenter"})
    note = book.add_format({"text_wrap": True, "valign": "vcenter", "font_color": "#34473F"})
    sheet.merge_range("A1:F1", title + " | " + spec["house_name"], title_style)
    sheet.set_row(0, 34)
    for i, value in enumerate([spec["issue"] + " | " + spec["audience"] + " | " + spec["purpose"],
                               spec["limitation"] + " " + spec["next_action"]], 1):
        sheet.merge_range(i, 0, i, 5, value, note)
        sheet.set_row(i, 32)
    sheet.set_landscape()
    sheet.set_paper(9)
    sheet.repeat_rows(HEADER)
    sheet.set_footer("&L" + spec["house_name"].replace("&", "&&") + " | " + spec["issue"] + "&R&P / &N")


def write_workbook(path, spec):
    kind = spec["slug"]
    rows = workbook_rows(spec)
    labels = list(rows[0])
    with render_pack.editable_workbook(path) as book:
        book.set_properties({"title": SCHEDULES[kind] + " | " + spec["house_name"], "created": datetime(2000, 1, 1)})
        money = book.add_format({"num_format": '"£"#,##0.00;[Red]("£"#,##0.00);"£"0.00', "valign": "top"})
        dates = book.add_format({"num_format": "dd mmm yyyy", "valign": "top"})
        wrap = book.add_format({"text_wrap": True, "valign": "top"})
        if kind == "cost-schedule":
            overview = book.add_worksheet("Cost summary")
            banner(overview, spec, "Cost summary", book)
            overview.set_column(0, 0, 28)
            overview.set_column(1, 5, 23)
            overview.merge_range("A4:F4", "Each option includes Base. Excluded lines do not contribute. A blank total has an open or invalid line.", wrap)
            overview.set_row(3, 31)
            values = totals(rows)
            book.define_name("CostScenarios", f"='Cost summary'!$A$7:$A${6+len(values)}")
            overview.add_table(HEADER, 0, HEADER+len(values), 5, {"columns": [{"header": c} for c in TOTAL_COLUMNS],
                               "style": "Table Style Medium 4"})
            for i, data in enumerate(values, HEADER+1):
                overview.write_string(i, 0, data[0])
                for j, formula in enumerate(summary_formula(i+1), 1):
                    overview.write_formula(i, j, formula, None if j == 3 else money, data[j])
            overview.freeze_panes(HEADER+1, 1)
            overview.fit_to_pages(1, 0)
        sheet = book.add_worksheet(TABS[kind])
        banner(sheet, spec, SCHEDULES[kind], book)
        if kind == "programme":
            sheet.write_string("A4", "Programme start")
            sheet.write_number("B4", serial(spec["start_date"]), dates)
            sheet.merge_range("C4:F4", "Calendar days. Successors start after each predecessor finishes. Dates are forecasts.", wrap)
            sheet.set_row(3, 30)
        sheet.add_table(HEADER, 0, HEADER+len(rows), len(labels)-1, {
            "name": {"cost-schedule": "CostLines", "programme": "Tasks", "decorator-finishes": "Finishes"}[kind],
            "columns": [{"header": c} for c in labels], "style": "Table Style Medium 4"})
        widths = [min(46, max(15, len(label)+4, max(len(str(r[label])) for r in rows)+2)) for label in labels]
        for j, width in enumerate(widths):
            sheet.set_column(j, j, width)
        sheet.freeze_panes(HEADER+1, 2)
        for i, row in enumerate(rows, HEADER+1):
            formulas = formulae(kind, labels, i+1)
            for j, (label, raw) in enumerate(row.items()):
                value = native(label, raw)
                style = money if label in AMOUNTS else dates if label in DATES else wrap
                if label in formulas:
                    sheet.write_formula(i, j, formulas[label], style, value)
                elif value != "":
                    sheet.write(i, j, value, style)
            height = max(math.ceil(len(str(v))/max(1, widths[j]-5)) for j, v in enumerate(row.values()))
            sheet.set_row(i, max(30, min(400, height*18+10)))
        if kind == "programme":
            col = labels.index("Days")
            sheet.data_validation(HEADER+1, col, HEADER+len(rows), col,
                                  {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 99999})


def portable_rows(spec):
    return [dict(House=spec["house_name"], Issue=spec["issue"], **row) for row in spec["rows"]]


def reader_body(spec):
    _, workbook, data = schedule_paths(spec, spec["issue"])
    xlsx, csv = Path(workbook).name, Path(data).name
    links = f'<p><a href="{quote(xlsx)}">Open editable workbook</a> · <a href="{quote(csv)}">Download CSV</a></p>'
    if spec["slug"] == "cost-schedule":
        for name, lo, hi, missing, _, _ in totals(spec["rows"]):
            detail = f"£{lo:,.2f} to £{hi:,.2f} priced"
            detail += f" · {missing} unresolved" if missing else " · all lines priced"
            links += f"<p><b>{escape(name)}</b> · {detail}</p>"
    sections = []
    for row in spec["rows"]:
        heading = (row["Room"] + " | " + row["Surface"] if "Surface" in row else
                   row.get("Scope") or row["Task ID"] + " | " + row["Task"])
        fields = "".join(f"<dt><b>{escape(k)}</b></dt><dd>{escape(str(v))}</dd>" for k, v in row.items() if v != "")
        sections.append(f"<section><h2>{escape(heading)}</h2><dl>{fields}</dl></section>")
    return links + '<style>dd{margin:0 0 .5em}section{break-inside:avoid;border-top:1px solid #b3c2b7;margin:1.3em 0} @media print{a{display:none}dl{columns:2}dd{break-before:avoid}}</style>' + "".join(sections)


def build_schedule(envelope, spec, selection_hash):
    root = envelope / "delivery"
    index, workbook, csv = schedule_paths(spec, spec["issue"])
    (root / index).parent.mkdir(parents=True)
    write_workbook(root / workbook, spec)
    (root / csv).write_bytes(render_pack.csv_bytes(portable_rows(spec)))
    title = SCHEDULES[spec["slug"]]
    (root / index).write_bytes(render_pack.html_page(spec, title, reader_body(spec)).encode())
    entry = f'<p><a href="{quote(index)}">Open the {escape(title.lower())}</a></p>'
    (root / "Start here.html").write_bytes(render_pack.html_page(spec, title, entry).encode())
    render_pack.seal(envelope, spec, selection_hash, spec["files"])


def verify_schedule(envelope, spec, manifest):
    archive = render_pack.verify_contents(envelope, spec, manifest, spec["files"])
    root = envelope / "delivery"
    index, workbook, csv = schedule_paths(spec, spec["issue"])
    if (root / csv).read_bytes() != render_pack.csv_bytes(portable_rows(spec)):
        raise ValueError("Portable CSV differs from the commissioned schedule")
    title = SCHEDULES[spec["slug"]]
    if (root / index).read_bytes() != render_pack.html_page(spec, title, reader_body(spec)).encode():
        raise ValueError("Offline reader differs from the issued schedule")
    if quote(index) not in Page((root / "Start here.html").read_bytes()).links:
        raise ValueError("Schedule is missing from the issue index")
    # Verify the actual cells, formulas, cached results, table coverage and workbook inventory.
    data = (root / workbook).read_bytes()
    kind = spec["slug"]
    tab = TABS[kind]
    rows = workbook_rows(spec)
    labels = list(rows[0])
    books = [openpyxl.load_workbook(io.BytesIO(data), data_only=mode) for mode in (False, True)]
    try:
        formulas, values = books[0][tab], books[1][tab]
        names = (["Cost summary"] if kind == "cost-schedule" else []) + [tab]
        if books[0].sheetnames != names or formulas.max_column != len(labels) or formulas.max_row != HEADER+1+len(rows):
            raise ValueError("Workbook differs from the commissioned tabs or row count")
        region = f"A{HEADER+1}:{get_column_letter(len(labels))}{formulas.max_row}"
        if ([c.value for c in formulas[HEADER+1]] != labels or
                not any(t.autoFilter and t.autoFilter.ref == region for t in formulas.tables.values())):
            raise ValueError("Schedule columns or table filters differ")
        if kind == "programme" and values["B4"].value.date().isoformat() != spec["start_date"]:
            raise ValueError("Programme start differs")
        for i, row in enumerate(rows, HEADER+2):
            expected = formulae(kind, labels, i)
            for j, (label, raw) in enumerate(row.items(), 1):
                cell = formulas.cell(i, j)
                value = values.cell(i, j).value
                if isinstance(value, datetime):
                    value = value.date().isoformat()
                wanted = float(raw) if raw != "" and label in AMOUNTS else raw
                if ((value if value is not None else "") != wanted or
                        (label in expected and cell.value != expected[label]) or
                        (label not in expected and cell.data_type == "f")):
                    raise ValueError(f"Workbook differs at {tab}!{cell.coordinate}")
        if kind == "cost-schedule":
            overview, cache = (book["Cost summary"] for book in books)
            expected_rows = totals(rows)
            named = books[0].defined_names.get("CostScenarios")
            if named is None or named.attr_text != f"'Cost summary'!$A$7:$A${6+len(expected_rows)}":
                raise ValueError("Workbook scenario list differs from the commissioned cost options")
            if overview.max_row != HEADER+1+len(expected_rows) or [c.value for c in overview[HEADER+1]] != list(TOTAL_COLUMNS):
                raise ValueError("Cost summary coverage differs")
            for i, row in enumerate(expected_rows, HEADER+2):
                actual = [c.value if c.value is not None else "" for c in cache[i]]
                if actual != row or [c.value for c in overview[i][1:]] != summary_formula(i):
                    raise ValueError(f"Cost summary differs on row {i}")
    finally:
        for book in books:
            book.close()
    return render_pack.receipt(spec, manifest, envelope, archive)
