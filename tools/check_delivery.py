"""Verify the portable link register, HTML navigation and nested room archives."""
import argparse
import csv
import hashlib
import io
import posixpath
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, data):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(data.decode("utf-8-sig"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])


def inspect(archive, label, counts):
    names = archive.namelist()
    if len(names) != len(set(names)) or archive.testzip():
        raise ValueError(f"{label}: repeated entry or damaged archive")
    pages = {n: Page(archive.read(n)) for n in names if n.lower().endswith(".html")}
    destinations = {name: set() for name in pages}
    for name, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme in ("https", "http", "mailto", "data"):
                continue
            path = unquote(url.path)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if not link or url.scheme or url.netloc or target not in names:
                raise ValueError(f"{label}/{name}: broken link {link!r}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"{label}/{name}: missing destination {link}")
            counts["local links"] += 1
            destinations[name].add(target)
    for name in names:
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(archive.read(name))) as nested:
                inspect(nested, f"{label}/{name}", counts)
    counts["archives"] += 1
    counts["HTML pages"] += len(pages)
    return destinations


def verify(path, *, expected_files=None):
    counts = Counter()
    with zipfile.ZipFile(path) as archive:
        destinations = inspect(archive, path.name, counts)
        if expected_files is not None:
            if set(archive.namelist()) != {*expected_files, "Link-register.csv"}:
                raise ValueError("The portable ZIP differs from the commissioned file list")
            reached = {"Start here.html"}
            pending = list(reached)
            while pending:
                new = destinations.get(pending.pop(), set()) - reached
                reached.update(new)
                pending.extend(new)
            missing = set(expected_files) - reached
            if missing:
                raise ValueError(f"Files unreachable from Start here.html: {sorted(missing)}")
        rows = list(csv.DictReader(io.StringIO(archive.read("Link-register.csv").decode("utf-8-sig"))))
        targets = set()
        for row in rows:
            name = row["path"]
            if not row["label"].strip() or not row["purpose"].strip() or name in targets:
                raise ValueError(f"Unclear or duplicate register entry: {name}")
            targets.add(name)
            if hashlib.sha256(archive.read(name)).hexdigest() != row["sha256"]:
                raise ValueError(f"File changed since link registration: {name}")
        missing = set(archive.namelist()) - targets - {"Link-register.csv"}
        if missing or "Start here.html" not in targets:
            raise ValueError(f"Incomplete link register: {sorted(missing)}")
        counts["registered files"] = len(rows)
    return dict(counts)


def verify_issue(outputs, *, archive_folder=None, expected_files=None):
    """Check a registered portable issue during revision save, including its loose portal."""
    register = outputs / "Link-register.csv"
    if not register.is_file():
        if expected_files is not None:
            raise ValueError("The commissioned issue needs a link register")
        return
    packs = []
    for candidate in (archive_folder or outputs).glob("*.zip"):
        with zipfile.ZipFile(candidate) as archive:
            if register.name in archive.namelist():
                packs.append(candidate)
    if len(packs) != 1:
        raise ValueError("A registered delivery needs one portable ZIP containing its register")
    verify(packs[0], expected_files=expected_files)
    with zipfile.ZipFile(packs[0]) as archive:
        if archive.read(register.name) != register.read_bytes():
            raise ValueError("Loose and portable link registers differ")
    with register.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            path = (outputs / row["path"]).resolve()
            if not path.is_relative_to(outputs.resolve()) or not path.is_file():
                raise ValueError(f"Missing loose delivery file: {row['path']}")
            with path.open("rb") as file:
                checksum = hashlib.file_digest(file, "sha256").hexdigest()
            if checksum != row["sha256"]:
                raise ValueError(f"Loose delivery differs from portable file: {row['path']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    print(verify(parser.parse_args().pack))
