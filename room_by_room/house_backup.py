"""Verified, single-house ZIP backups and no-overwrite restoration."""
from contextlib import contextmanager
import hashlib
import json
import os
import stat
import tempfile
from itertools import zip_longest
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .house_revisions import (inventory, local_path, records, regular_path, safe_relative,
                             stored_json, transfer, verify_revision)

HEADER = "backup.json"


def equivalent_checkout_text(staged, target, name):
    """Git may check public text out with LF or CRLF on different machines."""
    parts = safe_relative(name).parts
    if parts[0] in ("source", "models", "views", "handover", ".revision-work"):
        return False
    if parts[0] == "revisions" and parts[2:] != ("record.json",):
        return False
    if target.suffix.lower() not in (".md", ".csv", ".json", ".txt", ".py"):
        return False
    with staged.open("rb") as saved, target.open("rb") as current:
        return all(a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")
                   for a, b in zip_longest(saved, current, fillvalue=b""))


def publish_file(source, destination):
    """Publish on the same volume without exposing a partial file or replacing a winner."""
    if os.name == "nt":
        source.rename(destination)
    else:
        os.link(source, destination)


def manifest(archive, house_id):
    names = archive.namelist()
    if len(names) != len(set(names)) or HEADER not in names:
        raise ValueError("Missing backup manifest or duplicate archive members.")
    header = json.loads(archive.read(HEADER))
    if header.get("format") != 1 or header.get("house") != house_id:
        raise ValueError("Backup belongs to a different house or has an unknown format.")
    dirs, files = header["directories"], header["files"]
    if not isinstance(dirs, list) or not isinstance(files, dict) or "project.json" not in files:
        raise ValueError("Invalid backup inventory.")
    paths = set()
    directories = set(dirs)
    for name in [*dirs, *files]:
        path = safe_relative(name)
        key = name.casefold()
        if key in paths:
            raise ValueError(f"Conflicting backup path: {name}")
        paths.add(key)
        if path.parent != Path(".") and path.parent.as_posix() not in directories:
            raise ValueError(f"Missing parent directory: {name}")
    if set(names) != {HEADER, *("house/" + name for name in files)}:
        raise ValueError("Archive files differ from its manifest.")
    identity = json.loads(archive.read("house/project.json"))
    if identity["id"] != house_id:
        raise ValueError("Archived project identity differs from its manifest.")
    return header


def read_payload(archive, header, target=None):
    if target:
        for name in sorted(header["directories"]):
            (target / name).mkdir()
    for name, expected in header["files"].items():
        info = archive.getinfo("house/" + name)
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"Linked archive member: {name}")
        with archive.open("house/" + name) as src:
            if target is None:
                digest = transfer(src)
            else:
                with (target / name).open("xb") as dst:
                    digest = transfer(src, dst)
        if digest != expected:
            raise ValueError(f"Backup checksum differs: {name}")


@contextmanager
def recovery_archive(path, house_id, *, base_dir=None):
    """Present a full logical house while reading unchanged bytes from one pinned full ZIP."""
    with ZipFile(path) as current:
        meta = json.loads(current.read(HEADER))
        if meta.get("format") != 2:
            yield current
            return
        base_name = meta["base"]
        if len(safe_relative(base_name).parts) != 1 or base_name == path.name:
            raise ValueError("Invalid full backup name")
        with ZipFile(local_path(base_dir or path.parent, base_name)) as base:
            base_header = manifest(base, house_id)
            if hashlib.sha256(base.read(HEADER)).hexdigest() != meta["base_manifest_sha256"]:
                raise ValueError("Full backup manifest changed")
            sources = {digest: (base, "house/" + name) for name, digest in base_header["files"].items()}
            needed = set(meta["files"].values()) - sources.keys()
            members = current.namelist()
            if len(members) != len(set(members)) or set(members) != {HEADER, *("objects/" + d for d in needed)}:
                raise ValueError("Delta contents differ from the required objects")
            sources.update({d: (current, "objects/" + d) for d in needed})
            yield LogicalArchive(meta, sources)


class LogicalArchive:
    def __init__(self, meta, sources):
        self.meta = dict(meta, format=1)
        self.sources = sources

    def namelist(self):
        return [HEADER, *("house/" + name for name in self.meta["files"])]

    def member(self, name):
        return self.sources[self.meta["files"][name.removeprefix("house/")]]

    def read(self, name):
        if name == HEADER:
            return json.dumps(self.meta).encode()
        archive, key = self.member(name)
        return archive.read(key)

    def open(self, name):
        archive, key = self.member(name)
        return archive.open(key)

    def getinfo(self, name):
        archive, key = self.member(name)
        return archive.getinfo(key)


def full_base(directory, house_id):
    for path in sorted(directory.glob("*.zip"), key=lambda p: p.stat().st_mtime_ns, reverse=True):
        with ZipFile(path) as candidate:
            header = json.loads(candidate.read(HEADER))
            if header.get("format") == 1 and header.get("house") == house_id:
                known = set(manifest(candidate, house_id)["files"].values())
                return path, hashlib.sha256(candidate.read(HEADER)).hexdigest(), known
    return None


def backup_directory():
    configured = os.environ.get("HOUSE_BACKUP_DIR")
    directory = Path(configured).expanduser() if configured else Path.home() / "House Renovation Backups"
    if not directory.is_absolute():
        raise ValueError("HOUSE_BACKUP_DIR must be an absolute path to private storage.")
    return directory


def automatic_backup(root, destination, repo, *, staged_revision):
    """Replace the shared recovery point only after the full successor verifies."""
    from .house_revisions import _save_lock

    if any(destination.resolve().is_relative_to(p.resolve()) for p in (repo, root.parent)):
        raise ValueError("Choose a private backup destination outside the checkout and house library.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _save_lock(destination.parent):
        if os.path.lexists(destination):
            regular_path(destination)
            with ZipFile(destination) as previous:
                header = manifest(previous, stored_json(root / "project.json")["id"])
                if header.get("retention") != "latest":
                    raise ValueError("The automatic recovery path contains a separately managed archive.")
        with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
            replacement = Path(temp) / "replacement.zip"
            backup(root, replacement, repo, staged_revision=staged_revision, managed=True)
            if destination.exists():
                os.replace(replacement, destination)
            else:
                publish_file(replacement, destination)


def backup(root, destination, repo, *, staged_revision=None, managed=False):
    destination = destination.expanduser().absolute()
    for private_root in (repo, root.parent):
        if destination.resolve().is_relative_to(private_root.resolve()):
            raise ValueError("Choose a private backup destination outside the checkout and house library.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.path.lexists(destination):
        raise FileExistsError(f"Backup already exists: {destination}")
    house_id = stored_json(root / "project.json")["id"]
    before, dirs = inventory(root, house=True)
    sources = {name: root / name for name in before}
    archive_dirs = list(dirs)
    snapshots = [verify_revision(root, record["revision"]) for record in records(root)]
    if staged_revision is not None:
        # Include the prepared revision under its final name. Its working location
        # is excluded by the house inventory until the verified backup is durable.
        prefix = "revisions/" + staged_revision.name
        if prefix in dirs or prefix in before:
            raise FileExistsError(f"Revision already exists: {prefix}")
        staged_files, staged_dirs = inventory(staged_revision)
        archive_dirs.extend([prefix, *(prefix + "/" + name for name in staged_dirs)])
        sources.update({prefix + "/" + name: staged_revision / name for name in staged_files})
        snapshots.append(stored_json(staged_revision / "record.json"))
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        staged = Path(temp) / "house.zip"
        base = full_base(destination.parent, house_id) if staged_revision is not None and not managed else None
        hashes = {}
        with ZipFile(staged, "x", compression=ZIP_DEFLATED, allowZip64=True) as archive:
            for name, source in sources.items():
                member = "house/" + name
                if base:
                    with source.open("rb") as src:
                        hashes[name] = transfer(src)
                    if hashes[name] in base[2]:
                        continue
                    member = "objects/" + hashes[name]
                    base[2].add(hashes[name])
                with source.open("rb") as src, archive.open(member, "w", force_zip64=True) as dst:
                    hashes[name] = transfer(src, dst)
            for record in snapshots:
                for kind in ("inputs", "outputs"):
                    for name, expected in record[kind].items():
                        key = f"revisions/{record['revision']}/{kind}/{name}"
                        if hashes.get(key) != expected:
                            raise ValueError(f"Archived bytes differ from the recorded revision: {key}")
            header = dict(format=1, house=house_id, directories=archive_dirs, files=hashes)
            if managed:
                header["retention"] = "latest"
            if base:
                header.update(format=2, base=base[0].name, base_manifest_sha256=base[1])
            archive.writestr(HEADER, json.dumps(header))
        if inventory(root, house=True) != (before, dirs):
            raise ValueError("House files changed during backup. Finish saving and retry.")
        with recovery_archive(staged, house_id, base_dir=destination.parent) as archive:
            read_payload(archive, manifest(archive, house_id))
        if os.name != "nt":
            staged.chmod(0o600)
        publish_file(staged, destination)
    return len(hashes)


def restore(house_id, archive_path, target):
    target = target.absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Check all names and bytes in isolation before touching an existing house.
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".house-restore-") as temp:
        staged = Path(temp) / "house"
        staged.mkdir()
        try:
            with recovery_archive(Path(archive_path), house_id) as archive:
                header = manifest(archive, house_id)
                read_payload(archive, header, staged)
        except (BadZipFile, KeyError, TypeError) as exc:
            raise ValueError(f"Invalid house backup: {exc}") from exc
        for record in records(staged):
            verify_revision(staged, record["revision"])
        if not os.path.lexists(target):
            staged.rename(target)
            return len(header["files"])
        regular_path(target)
        if not target.is_dir():
            raise ValueError(f"Restore target is not a directory: {target}")
        if any(target.iterdir()):
            project = local_path(target, "project.json")
            if not project.is_file() or stored_json(project).get("id") != house_id:
                raise ValueError("Restore target contains a different or unidentified project.")
        # Keep current private files and local edits intact. Check every conflict before installing any files.
        existing_files, existing_dirs = inventory(target, house=True)
        existing_names = {name.casefold(): name for name in [*existing_files, *existing_dirs]}
        for name in [*header["directories"], *header["files"]]:
            if existing_names.get(name.casefold(), name) != name:
                raise ValueError(f"Restore name conflicts with an existing path: {name}")
        for name in header["directories"]:
            dest = local_path(target, name)
            if dest.exists() and not dest.is_dir():
                raise ValueError(f"Restore conflicts with existing file: {name}")
        missing = []
        for name, expected in header["files"].items():
            dest = local_path(target, name)
            if not dest.exists():
                missing.append(name)
                continue
            if dest.is_file():
                with dest.open("rb") as stream:
                    if transfer(stream) == expected:
                        continue
                if equivalent_checkout_text(staged / name, dest, name):
                    continue
            raise ValueError(f"Restore conflicts with {name}. Recover the backup in a fresh folder to compare.")
        for name in sorted(header["directories"]):
            local_path(target, name).mkdir(exist_ok=True)
        for name in missing:
            publish_file(staged / name, local_path(target, name))
        return len(missing)
