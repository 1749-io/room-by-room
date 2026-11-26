"""Check the staged public distribution against its reviewed binary asset inventory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

INVENTORY = "examples/asset-inventory.json"
PRIVATE = {"houses", "private-backups", "house renovation backups", ".revision-work", "handover-answers",
           ".codex", ".env", ".ssh", "backups"}
TEXT_TYPES = {".py", ".md", ".txt", ".dot", ".svg", ".yaml", ".yml", ".json", ".csv", ".license"}
TEXT_NAMES = {"LICENSE", ".gitignore", ".gitattributes"}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def private_path(name):
    parts = tuple(part.casefold() for part in PurePosixPath(name).parts)
    return bool(PRIVATE.intersection(parts) or parts[0] in {"source", "models", "views", "handover"})


def check_history(root):
    trees = set(git(root, "log", "--all", "HEAD", "--format=%T").splitlines())
    paths = set()
    for tree in trees:
        paths.update(filter(None, git(root, "ls-tree", "-rz", "--name-only", tree.decode()).split(b"\0")))
    blocked = {name.decode() for name in paths if private_path(name.decode())}
    if paths:
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "--no-index", "--stdin", "-z"],
                                 input=b"\0".join(sorted(paths)) + b"\0", stdout=subprocess.PIPE)
        if ignored.returncode not in (0, 1):
            ignored.check_returncode()
        blocked.update(p.decode() for p in ignored.stdout.split(b"\0") if p)
    return [f"Private or ignored path in Git history: {p}" for p in sorted(blocked)]


def check(root):
    errors = []
    inventory = json.loads(git(root, "show", ":" + INVENTORY))
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("Supply the reviewed example asset inventory")
    entries = git(root, "ls-files", "--stage", "-z").decode().split("\0")
    reviewed = set()
    for entry in filter(None, entries):
        header, name = entry.split("\t", 1)
        mode, blob, stage = header.split()
        path = PurePosixPath(name)
        if mode not in {"100644", "100755"} or stage != "0" or private_path(name):
            errors.append(f"Private or unsupported entry: {name}")
            continue
        data = git(root, "cat-file", "blob", blob)
        if name in inventory:
            row = inventory[name]
            if (path.parts[0] != "examples" or hashlib.sha256(data).hexdigest() != row.get("sha256")
                    or not row.get("origin") or not row.get("rights")):
                errors.append(f"Review changed asset, origin and rights: {name}")
            reviewed.add(name)
        elif name == ".github/CODEOWNERS" or path.name in TEXT_NAMES or path.suffix in TEXT_TYPES:
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError:
                errors.append(f"Undeclared binary: {name}")
            if b"\0" in data:
                errors.append(f"Binary content in text: {name}")
        else:
            errors.append(f"Unreviewed file type: {name}")
    for name in sorted(set(inventory) - reviewed):
        errors.append(f"Missing reviewed asset: {name}")
    ignored = git(root, "ls-files", "-ci", "--exclude-from=.gitignore", "-z")
    errors.extend("Tracked despite ignore rules: " + p for p in ignored.decode().split("\0") if p)
    return errors


if __name__ == "__main__":
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    command.add_argument("--history", action="store_true", help="Also inspect every reachable historical tree")
    args = command.parse_args()
    errors = check(args.root)
    if args.history:
        errors.extend(check_history(args.root))
    if errors:
        raise SystemExit("\n".join(errors))
    print("Public file types, private paths and reviewed asset hashes pass.")
