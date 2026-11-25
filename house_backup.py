"""Verified, single-house ZIP backups and no-overwrite restoration."""
import json
import os
import stat
import tempfile
from itertools import zip_longest
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from house_revisions import (inventory, local_path, records, regular_path, safe_relative,
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
        with archive.open(info) as src:
            if target is None:
                digest = transfer(src)
            else:
                with (target / name).open("xb") as dst:
                    digest = transfer(src, dst)
        if digest != expected:
            raise ValueError(f"Backup checksum differs: {name}")


def backup_directory():
    configured = os.environ.get("HOUSE_BACKUP_DIR")
    directory = Path(configured).expanduser() if configured else Path.home() / "House Renovation Backups"
    if not directory.is_absolute():
        raise ValueError("HOUSE_BACKUP_DIR must be an absolute path to private storage.")
    return directory


def backup(root, destination, repo, *, staged_revision=None):
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
        hashes = {}
        with ZipFile(staged, "x", compression=ZIP_DEFLATED, allowZip64=True) as archive:
            for name, source in sources.items():
                with source.open("rb") as src, archive.open("house/" + name, "w", force_zip64=True) as dst:
                    hashes[name] = transfer(src, dst)
            for record in snapshots:
                for kind in ("inputs", "outputs"):
                    for name, expected in record[kind].items():
                        key = f"revisions/{record['revision']}/{kind}/{name}"
                        if hashes.get(key) != expected:
                            raise ValueError(f"Archived bytes differ from the recorded revision: {key}")
            archive.writestr(HEADER, json.dumps(dict(format=1, house=house_id, directories=archive_dirs, files=hashes)))
        if inventory(root, house=True) != (before, dirs):
            raise ValueError("House files changed during backup. Finish saving and retry.")
        with ZipFile(staged) as archive:
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
            with ZipFile(archive_path) as archive:
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
