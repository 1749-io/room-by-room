"""Open the extracted schedule issues and recalculate edits in an independent spreadsheet application."""
import argparse
from datetime import date
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote
import zipfile

import fitz
import openpyxl
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.smoke_pack_browser import check

ISSUES = {"FINISH": "decorator-finishes", "COST": "cost-schedule", "PROG": "programme"}


def edit_and_recalculate(root, office):
    changes = root / "Edited copies"
    changes.mkdir()
    cost = openpyxl.load_workbook(io.BytesIO(next((root / "COST").rglob("*.xlsx")).read_bytes()))
    sheet = cost["Cost lines"]
    for row in sheet.iter_rows(min_row=7):
        if row[0].value == "Wall paint and preparation materials":
            row[6].value, row[7].value = 75, 100
        if row[0].value == "Shelf fitting and delivery":
            row[6].value, row[7].value = 40, 70
    cost.save(changes / "Cost.xlsx")
    cost.close()
    plan = openpyxl.load_workbook(io.BytesIO(next((root / "PROG").rglob("*.xlsx")).read_bytes()))
    sheet = plan["Programme"]
    cols = {c.value: c.column for c in sheet[6]}
    rows = {sheet.cell(r, 1).value: r for r in range(7, sheet.max_row+1)}
    sheet.cell(rows["SUR"], cols["Days"]).value = 4
    plan.save(changes / "Programme.xlsx")
    sheet.cell(rows["SUR"], cols["Days"]).value = None
    plan.save(changes / "Unknown duration.xlsx")
    plan.close()
    result = root / "Recalculated"
    result.mkdir()
    subprocess.run([office, "-env:UserInstallation=" + (root / "calc-profile").as_uri(), "--headless",
                    "--convert-to", "xlsx", "--outdir", str(result), *map(str, sorted(changes.glob("*.xlsx")))],
                   check=True, capture_output=True, timeout=120)
    for path in changes.glob("*.xlsx"):
        book = openpyxl.load_workbook(io.BytesIO((result / path.name).read_bytes()), data_only=True)
        try:
            if path.stem == "Cost":
                overview = list(book["Cost summary"].values)
                assert overview[6][:6] == ("Base", 220, 315, 0, 220, 315), overview[6]
                assert overview[7][:6] == ("Add shelves", 429, 554, 0, 429, 554), overview[7]
            else:
                sheet = book["Programme"]
                finish = sheet.cell(rows["FIT"], cols["Forecast finish"]).value
                if path.stem == "Programme":
                    assert finish.date() == date(2027, 1, 21), finish
                    assert sheet.cell(rows["CHOOSE"], cols["Timing"]).value == "Late"
                else:
                    assert finish in (None, ""), finish
                    assert sheet.cell(rows["CHOOSE"], cols["Timing"]).value == "Awaiting duration"
        finally:
            book.close()
    print("Calc recalculated revised costs, a delayed decision and a dependent task with an unknown date.")


def exercise(home, root, office):
    for issue in [*ISSUES, "HOUSE-TRADE"]:
        dest = root / issue
        with zipfile.ZipFile(next((home / "revisions" / issue / "outputs/pack").glob("*.zip"))) as archive:
            archive.extractall(dest)
        for width in (390, 1280):
            pages, clicks = check(dest / "Start here.html", width=width)
            print(f"{issue} at {width}px | {pages} offline pages, {clicks} links")
    with sync_playwright() as api:
        browser = api.chromium.launch()
        page = browser.new_page(accept_downloads=True, viewport={"width": 390, "height": 844})
        page.context.set_offline(True)
        for issue, kind in ISSUES.items():
            for directory in (root / issue, root / "HOUSE-TRADE"):
                page.goto((directory / "Start here.html").as_uri())
                page.locator(f'a[href*="/{kind}/Read"]').click()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), kind
                for ext in (".xlsx", ".csv"):
                    link = page.locator(f'a[href$="{ext}"]')
                    filename = unquote(link.get_attribute("href"))
                    with page.expect_download() as download:
                        link.click()
                    expected = root / issue / "Schedules" / kind / filename
                    assert download.value.path().read_bytes() == expected.read_bytes(), filename
                printed = page.pdf(format="A4", margin={edge: "12mm" for edge in ("top", "right", "bottom", "left")})
                with fitz.open(stream=printed, filetype="pdf") as pdf:
                    text = " ".join(" ".join(p.get_text().split()) for p in pdf)
                    markers = {"FINISH": ["AL-04", "AL-01", "Water-based eggshell"],
                               "COST": ["£210.00", "£469.00", "Shelf fitting and delivery"],
                               "PROG": ["2027-01-18", "Keep library clear during drilling"]}[issue]
                    assert all(marker in text for marker in markers), (issue, markers)
        browser.close()
    if office:
        edit_and_recalculate(root, office)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--house", type=Path, help="Already issued fictional Alder Cottage")
    parser.add_argument("--office", help="Path to the LibreOffice executable")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="Trade schedule reader ") as temp:
        root = Path(temp)
        home = args.house
        if home is None:
            subprocess.run([sys.executable, str(ROOT / "examples/trade-schedules/replay.py"), str(root / "private")], check=True)
            home = root / "private/houses/alder-cottage"
        exercise(home, root, args.office)
