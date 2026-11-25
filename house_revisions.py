"""Append-only house outputs. Published records are portable, payloads stay private."""
import hashlib
import json
import ntpath
import os
import re
import shutil
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

WORK = ".revision-work"
HISTORY = "revisions"
BLOCK = 1024 * 1024


def safe_relative(name):
    """Accept paths that name the same ordinary files on Windows and POSIX."""
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid relative path: {name!r}")
    for part in name.split("/"):
        reserved = ntpath.isreserved(part) if hasattr(ntpath, "isreserved") else PureWindowsPath(part).is_reserved()
        if (part in ("", ".", "..") or part.endswith((" ", ".")) or
                re.search(r'[<>:"\\|?*\x00-\x1f]', part) or reserved):
            raise ValueError(f"Unsafe relative path: {name!r}")
    return Path(*name.split("/"))


def regular_path(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) == 0xA0000003:
        raise ValueError(f"Linked path is outside the snapshot contract: {path}")
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError(f"Expected an ordinary file or directory: {path}")
    return info


def local_path(root, name):
    path = root
    regular_path(path)
    for part in safe_relative(name).parts:
        path = path / part
        if os.path.lexists(path):
            regular_path(path)
    return path


def inventory(root, *, house=False):
    """List files and directories, including empty ones. Reject portable-name collisions."""
    files, directories = {}, []
    def walk(folder):
        names = set()
        for path in sorted(folder.iterdir()):
            if house and folder == root / WORK and path.name.startswith(".staging-"):
                continue
            rel = path.relative_to(root).as_posix()
            safe_relative(rel)
            if path.name.casefold() in names:
                raise ValueError(f"Case collision at {rel}")
            names.add(path.name.casefold())
            info = regular_path(path)
            if stat.S_ISDIR(info.st_mode):
                directories.append(rel)
                walk(path)
            else:
                files[rel] = (info.st_size, info.st_mtime_ns, info.st_ino)
    regular_path(root)
    walk(root)
    return files, directories


def transfer(source, destination=None):
    digest = hashlib.sha256()
    while True:
        data = source.read(BLOCK)
        if not data:
            return digest.hexdigest()
        digest.update(data)
        if destination is not None:
            destination.write(data)


def copy_file(source, destination):
    regular_path(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("xb") as dst:
        before = os.fstat(src.fileno())
        digest = transfer(src, dst)
        after = source.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError(f"Source changed during copying: {source}. Finish writing and retry.")
        return digest


def stored_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, content):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(content, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def revision_id(value):
    # One spelling per ID even when a house moves between operating systems.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise ValueError("Use a revision ID of up to 64 letters, digits, underscores or hyphens.")
    safe_relative(value)
    return value.upper()


def toolkit_checkout():
    root = Path(__file__).resolve().parent
    if not (root / ".git").exists():
        return None
    try:
        def git(*args):
            return subprocess.check_output(["git", "--no-optional-locks", "-C", str(root), *args],
                                           stderr=subprocess.DEVNULL, timeout=10)
        return {"commit": git("rev-parse", "HEAD").decode("ascii").strip(),
                "local_changes": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        return None


def record_dir(root, revision):
    return local_path(root, f"{HISTORY}/{revision_id(revision)}")


def check_files(folder, expected):
    files, _ = inventory(folder)
    if files.keys() != expected.keys():
        raise ValueError(f"Missing or unexpected private files in {folder}. Check the backup.")
    for name in files:
        with (folder / name).open("rb") as stream:
            if transfer(stream) != expected[name]:
                raise ValueError(f"Checksum differs for {folder / name}")


def verify_revision(root, revision):
    folder = record_dir(root, revision)
    record = stored_json(local_path(folder, "record.json"))
    if record["revision"] != folder.name or record["house"] != stored_json(root / "project.json")["id"]:
        raise ValueError(f"Revision identity mismatch in {folder}")
    for kind in ("inputs", "outputs"):
        check_files(local_path(folder, kind), record[kind])
    return record


def begin(root, revision, parent=None, inputs=()):
    revision = revision_id(revision)
    final = record_dir(root, revision)
    work = local_path(root, WORK)
    work.mkdir(exist_ok=True)
    draft = local_path(work, revision)
    if final.exists() or draft.exists():
        raise ValueError(f"{revision} already exists. Resume its open draft or choose a new revision.")
    parent = revision_id(parent) if parent else None
    with tempfile.TemporaryDirectory(dir=work, prefix=".staging-") as temp:
        stage = Path(temp) / revision
        stage.mkdir()
        (stage / "inputs").mkdir()
        out = stage / "outputs"
        if parent:
            previous = verify_revision(root, parent)
            shutil.copytree(record_dir(root, parent) / "outputs", out)
            check_files(out, previous["outputs"])
        else:
            out.mkdir()
        captured = {}
        context = [name for name in ("brief.md", "decisions.md") if (root / name).is_file()]
        for name in dict.fromkeys([*context, *inputs]):
            source = local_path(root, name)
            if safe_relative(name).parts[0] == WORK or not source.is_file():
                raise ValueError(f"Select a saved house input file: {name}")
            captured[name] = copy_file(source, stage / "inputs" / safe_relative(name))
        write_json(stage / "draft.json", {"revision": revision, "parent": parent, "inputs": captured})
        stage.rename(draft)
    return draft / "outputs"


@contextmanager
def _save_lock(work):
    # OS locks are released if a writer exits. A persistent, ignored lock file
    # avoids unlink/recreate races and never enters the house archive.
    with (work / ".staging-save.lock").open("a+b") as stream:
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Another house save is in progress. Retry when it finishes.") from exc
        yield


def save(root, revision, *, change, why, author, affects, next_step):
    from house_backup import backup, backup_directory

    revision = revision_id(revision)
    details = dict(change=change, why=why, author=author, affects=affects, next_step=next_step)
    if any(not value.strip() for value in details.values()):
        raise ValueError("Record who made the change, what changed, why, what it affects and the next step.")
    final = record_dir(root, revision)
    if final.exists():
        raise ValueError(f"{revision} is already saved. Start a new revision for further work.")
    draft = local_path(root, f"{WORK}/{revision}")
    base = stored_json(local_path(draft, "draft.json"))
    if base["revision"] != revision:
        raise ValueError("The draft revision differs from its folder.")
    if base["parent"]:
        verify_revision(root, base["parent"])
    check_files(local_path(draft, "inputs"), base["inputs"])
    out = local_path(draft, "outputs")
    before, folders = inventory(out)
    if not before:
        raise ValueError("Add at least one output to the draft before saving.")
    with tempfile.TemporaryDirectory(dir=draft.parent, prefix=".staging-") as temp:
        stage = Path(temp) / revision
        stage.mkdir()
        shutil.copytree(draft / "inputs", stage / "inputs")
        check_files(stage / "inputs", base["inputs"])
        (stage / "outputs").mkdir()
        for name in folders:
            (stage / "outputs" / name).mkdir()
        hashes = {name: copy_file(out / name, stage / "outputs" / name) for name in before}
        if inventory(out) != (before, folders):
            raise ValueError("Outputs changed during save. Finish writing the draft and retry.")
        with _save_lock(draft.parent):
            if final.exists():
                raise ValueError(f"{revision} is already saved. Start a new revision for further work.")
            saved = datetime.now(timezone.utc)
            house_id = stored_json(root / "project.json")["id"]
            filename = f"{house_id}/{revision}-{saved:%Y%m%dT%H%M%S%fZ}.zip"
            archive = backup_directory() / safe_relative(filename)
            record = dict(version=1, house=house_id, toolkit=toolkit_checkout(), backup=filename,
                          saved=saved.isoformat(), **base, **details, outputs=hashes)
            write_json(stage / "record.json", record)
            final.parent.mkdir(exist_ok=True)
            backup(root, archive, Path(__file__).resolve().parent, staged_revision=stage)
            try:
                stage.rename(final)
            except OSError as exc:
                raise OSError(f"Backup verified at {archive}, but publishing {final} failed: {exc}") from exc
    return final


def records(root):
    folder = local_path(root, HISTORY)
    if not folder.exists():
        return []
    return sorted((stored_json(local_path(root, path.relative_to(root).as_posix()))
                   for path in folder.glob("*/record.json")), key=lambda item: (item["saved"], item["revision"]))


def open_drafts(root):
    work = local_path(root, WORK)
    return sorted(p.parent.name for p in work.glob("*/draft.json")
                  if not (record_dir(root, p.parent.name) / "record.json").exists())


def describe(record, *, files=False):
    heading = f"{record['revision']} | {record['saved']} | {record['author']}"
    if record["parent"]:
        heading += f" | based on {record['parent']}"
    lines = [heading, record["change"], f"Why: {record['why']}", f"Affects: {record['affects']}",
             f"Next: {record['next_step']}"]
    if files:
        if record.get("backup"):
            lines.append(f"Private backup (relative to backup directory): {record['backup']}")
        toolkit = record.get("toolkit")
        if toolkit:
            state = "with local changes" if toolkit["local_changes"] else "clean checkout"
            lines.append(f"Toolkit at save: {toolkit['commit']} ({state})")
        for kind in ("inputs", "outputs"):
            for name in record[kind]:
                lines.append(f"  {HISTORY}/{record['revision']}/{kind}/{name}")
    return "\n".join(lines)
