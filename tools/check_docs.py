"""Check local Markdown links in the tracked toolkit documentation."""
import argparse
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit


def prose(page):
    fence = ""
    for line in page.read_text(encoding="utf-8-sig").splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker and (not fence or marker[1].startswith(fence)):
            fence = "" if fence else marker[1]
        elif not fence:
            yield line


def anchors(page):
    found = set()
    for line in prose(page):
        heading = re.match(r"^#{1,6}\s+(.+)", line)
        if heading:
            title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading[1]).lower()
            slug = "".join(ch for ch in title if ch in " -_" or ch.isalnum()
                           or unicodedata.category(ch).startswith("M")).strip().replace(" ", "-")
            name = slug
            i = 0
            while name in found:
                i += 1
                name = f"{slug}-{i}"
            found.add(name)
        found.update(re.findall(r'<a\s+(?:id|name)="([^"]+)"', line))
    return found


def check(root):
    files = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    tracked = {root / name for name in files if name}
    dirs = {parent for path in tracked for parent in path.parents}
    failures = []
    headings = {}
    for page in sorted(tracked):
        rel = page.relative_to(root)
        # House templates contain links interpreted after installation in a house.
        if page.suffix != ".md" or rel.parts[0] in {"houses", "templates", ".codex"}:
            continue
        for line in prose(page):
            for raw in re.findall(r"\]\((<[^>]+>|[^)]+)\)", line):
                target = urlsplit(raw.strip("<>"))
                if target.scheme or target.netloc:
                    continue
                path = (page.parent / unquote(target.path)).resolve() if target.path else page
                if not path.is_relative_to(root) or (path not in tracked and path not in dirs):
                    failures.append(f"{rel}: missing {raw}")
                elif path in tracked and path.suffix == ".md" and target.fragment:
                    if path not in headings:
                        headings[path] = anchors(path)
                    if unquote(target.fragment) not in headings[path]:
                        failures.append(f"{rel}: missing heading {raw}")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    errors = check(parser.parse_args().root.resolve())
    if errors:
        raise SystemExit("\n".join(sorted(set(errors))))
    print("Tracked toolkit documentation links resolve.")
