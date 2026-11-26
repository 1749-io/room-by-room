"""Read the five extracted sample editions and forward the individual room HTML offline."""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.smoke_pack_browser import check


def exercise(home, target):
    for issue in ("ROOM", "DRAWING", "SHOP", "COMPLETE", "HOUSE"):
        output = home / "revisions" / issue / "outputs/pack"
        dest = target / issue
        with zipfile.ZipFile(next(output.glob("*.zip"))) as archive:
            archive.extractall(dest)
        for width in (390, 1280):
            pages, clicks = check(dest / "Start here.html", width=width)
            print(f"{issue} at {width}px | {pages} pages / {clicks} HTML links")
    # A forwarded room HTML has to work in a folder containing only that file.
    forwarded = target / "Forwarded room.html"
    shutil.copyfile(next((target / "HOUSE/Rooms").rglob("*.html")), forwarded)
    with sync_playwright() as app:
        browser = app.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, accept_downloads=True)
        page.context.set_offline(True)
        page.goto(forwarded.as_uri())
        assert "reading chair" in page.locator("main").inner_text()
        assert page.locator("img").first.evaluate("async img => { await img.decode(); return img.naturalWidth > 0 }")
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        page.goto((target / "HOUSE/Start here.html").as_uri())
        for suffix in (".csv", ".xlsx"):
            link = page.locator(f'a[href$="{suffix}"]')
            with page.expect_download() as result:
                link.click()
            expected = next((target / "SHOP/Schedules").glob("*" + suffix))
            assert result.value.path().read_bytes() == expected.read_bytes()
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--house", type=Path, help="Existing saved Alder Cottage fixture")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="Independent pack reader ") as directory:
        root = Path(directory)
        home = args.house
        if home is None:
            work = root / "example"
            subprocess.run([sys.executable, str(ROOT / "examples/component-pack/replay.py"), str(work)], check=True)
            home = work / "houses/alder-cottage"
        exercise(home.resolve(), root / "extracted")
