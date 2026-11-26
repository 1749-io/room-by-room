"""Append-only house outputs. Published records are portable, payloads stay private."""
import csv
import hashlib
import io
import json
import ntpath
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

WORK = ".revision-work"
HISTORY = "revisions"
BLOCK = 1024 * 1024


def publish_directory(staged, target):
    """Install a complete directory, allowing a short Windows file-indexer lock to clear."""
    for delay in (0.05, 0.15, 0.4, 1.0, None):
        if target.exists():
            raise FileExistsError(f"Destination already exists: {target}")
        try:
            staged.rename(target)
            return
        except PermissionError as exc:
            if getattr(exc, "winerror", None) not in (5, 32, 33) or delay is None:
                raise
            time.sleep(delay)


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


def begin(root, revision, parent=None, inputs=(), *, pack_request=None):
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
        if parent and pack_request:
            # Old delivery files are never inherited into a new recipient issue.
            verify_revision(root, parent)
            out.mkdir()
        elif parent:
            previous = verify_revision(root, parent)
            shutil.copytree(record_dir(root, parent) / "outputs", out)
            check_files(out, previous["outputs"])
        else:
            out.mkdir()
        captured = {}
        context = [name for name in ("brief.md", "decisions.md", "CHECKLIST.md", "survey-returns.csv", "cad-assumptions.csv",
                                     "design-states.json", "visual-approvals.json") if (root / name).is_file()]
        if (root / "exterior-views.csv").is_file():
            context.append("exterior-views.csv")
        context.extend(p.relative_to(root).as_posix() for p in sorted(local_path(root, "handover-answers").glob("*.json")))
        for name in dict.fromkeys([*context, *inputs]):
            source = local_path(root, name)
            if safe_relative(name).parts[0] == WORK or not source.is_file():
                raise ValueError(f"Select a saved house input file: {name}")
            captured[name] = copy_file(source, stage / "inputs" / safe_relative(name))
        base = {"revision": revision, "parent": parent, "inputs": captured}
        if pack_request:
            import house_delivery
            if safe_relative(pack_request).parts[0] == WORK:
                raise ValueError("Select a house request outside the revision work area")
            if pack_request not in captured:
                captured[pack_request] = copy_file(local_path(root, pack_request),
                                                   stage / "inputs" / safe_relative(pack_request))
            request = house_delivery.read_request(stage / "inputs" / safe_relative(pack_request))
            for name in house_delivery.context_files(root, request):
                if name not in captured:
                    captured[name] = copy_file(local_path(root, name), stage / "inputs" / safe_relative(name))
            base["pack_request"] = pack_request
        write_json(stage / "draft.json", base)
        publish_directory(stage, draft)
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


QUESTION_KINDS = ("visual", "scope", "timing", "budget", "administration")


def decision_fields(out, question, kind, image, description):
    if all(v is None for v in (question, kind, image, description)):
        return {}
    if not question or not question.strip():
        raise ValueError("Supply the homeowner question.")
    kind = kind or "visual"
    if kind not in QUESTION_KINDS:
        raise ValueError("Choose a supported question kind.")
    fields = dict(question=question.strip(), question_kind=kind)
    if image is None and description is None and kind != "visual":
        return fields
    if not image or not description or not description.strip():
        raise ValueError("A visual question requires --ask-image and --image-description.")
    path = local_path(out, image)
    formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
    if not path.is_file() or path.suffix.lower() not in formats:
        raise ValueError("Choose a PNG, JPEG or WebP from this revision's outputs.")
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Install Pillow in the project Python environment to verify decision images.") from exc
    data = path.read_bytes()
    try:
        with Image.open(io.BytesIO(data)) as opened:
            if opened.format != formats[path.suffix.lower()]:
                raise ValueError("Decision image format differs from its filename.")
            opened.verify()
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
    except (OSError, SyntaxError) as exc:
        raise ValueError("The decision image could not be decoded.") from exc
    fields["question_image"] = dict(path=image, description=description.strip(), sha256=hashlib.sha256(data).hexdigest())
    return fields


def ask(root, revision, question, kind=None, image=None, description=None):
    if not question or not question.strip():
        raise ValueError("Supply the homeowner question.")
    revision = revision_id(revision)
    work = local_path(root, WORK)
    with _save_lock(work):
        draft = local_path(root, f"{WORK}/{revision}")
        if record_dir(root, revision).exists() or not (draft / "draft.json").is_file():
            raise ValueError("Choose an open revision for a new question.")
        if kind == "scope":
            base = stored_json(draft / "draft.json")
            remaining = furnished_actions(root, revision, base["parent"], draft / "outputs")
            if remaining:
                raise ValueError("Continue the agreed furnished room: " + " | ".join(remaining))
        fields = decision_fields(draft / "outputs", question, kind, image, description)
        staged = dict(revision=revision, **fields)
        receipt = local_path(draft, "decision-preview.json")
        if receipt.exists():
            if stored_json(receipt) != staged:
                raise ValueError("This revision already has a different question or image. Use a new revision.")
        else:
            with tempfile.TemporaryDirectory(dir=work, prefix=".staging-question-") as temp:
                pending = Path(temp) / "decision.json"
                write_json(pending, staged)
                pending.rename(receipt)
        return staged


def verify_room_pack(outputs, room, revision, stages, *, photo_quality=False, require_windows=True, require_details=True, require_heads=True):
    """A full issue must actually carry the current, camera-reviewed finish photos."""
    from PIL import Image

    prefix = Path(HISTORY, revision, "outputs")

    def issued(name):
        relative = safe_relative(name)
        if not relative.is_relative_to(prefix):
            raise ValueError(f"{room.name}: link this revision's issued output: {name}")
        path = local_path(outputs, relative.relative_to(prefix).as_posix())
        if not path.is_file():
            raise ValueError(f"{room.name}: missing issued file: {path.name}")
        return path

    hero = issued(stages["final-ai"]["evidence"])
    handover = issued(stages["handover"]["evidence"])
    checks = room / "finish-checks.csv"
    photos = set()
    required_images = {}
    if checks.is_file():
        with checks.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["revision"] != revision or row["kind"] != "ai-colour":
                    continue
                photo, camera = issued(row["evidence"]), issued(row["source"])
                if row["result"] != "pass" or photo.suffix.lower() not in {".jpg", ".jpeg", ".webp", ".png"}:
                    raise ValueError(f"{room.name}: review the final photo beside its furnished camera")
                for source_image in (photo, camera):
                    with Image.open(source_image) as opened:
                        opened.verify()
                with photo.open("rb") as image, camera.open("rb") as source:
                    final_digest, camera_digest = transfer(image), transfer(source)
                    if final_digest == camera_digest:
                        raise ValueError(f"{room.name}: the final photo duplicates the Blender camera")
                photos.add(photo)
                required_images[photo] = final_digest
                required_images[camera] = camera_digest
    if hero not in photos:
        raise ValueError(f"{room.name}: link the reviewed final photo in the final-ai row")
    if photo_quality:
        import house_photos
        house_photos.review(outputs, room, revision, require_windows=require_windows, require_details=require_details, require_heads=require_heads)
        for suffix in (".json", "-brief.json"):
            item = local_path(outputs, f"photo-reviews/{room.name}{suffix}")
            required_images[item] = house_photos.digest(item)
    expected = set(required_images.values())
    sizes = {path.stat().st_size for path in required_images}
    archives = [handover] if handover.suffix.lower() == ".zip" else outputs.rglob("*.zip")
    for archive in archives:
        with zipfile.ZipFile(archive) as pack:
            if not any(Path(entry.filename).suffix.lower() in {".html", ".htm", ".pdf"} and entry.file_size
                       for entry in pack.infolist()):
                continue
            included = set()
            for entry in pack.infolist():
                if not entry.is_dir() and entry.file_size in sizes:
                    with pack.open(entry) as content:
                        included.add(transfer(content))
            if expected <= included:
                return
    raise ValueError(f"{room.name}: include the final photo(s), checked camera(s) and presentation in the downloadable room pack")


def furnished_actions(root, revision, parent=None, outputs=None, *, completed=None):
    """Use room reviews and the native camera inventory, including at first publication."""
    actions = []
    folder = outputs if outputs is not None else record_dir(root, revision) / "outputs"
    camera_rooms = {p.name.removesuffix(".camera.json") for p in (folder / "openings").glob("*.camera.json")}
    if camera_rooms and not (any(folder.rglob("*.blend")) and any(
            p.suffix.lower() in {".png", ".jpeg", ".jpg", ".webp"} for p in folder.rglob("*"))):
        camera_rooms.clear()
    for register in sorted((root / "rooms").glob("*/review.csv")):
        with register.open(encoding="utf-8-sig", newline="") as stream:
            stages = {row["stage"]: row for row in csv.DictReader(stream)}
        camera = stages.get("blender", {})
        room = register.parent
        current_camera = camera.get("status") == "pass" and camera.get("revision") == revision
        inherited_camera = parent and camera.get("status") == "pass" and camera.get("revision") == parent
        if room.name not in camera_rooms and not (current_camera or inherited_camera):
            continue
        brief_file = room / "README.md"
        brief = brief_file.read_text(encoding="utf-8-sig") if brief_file.is_file() else ""
        if re.search(r"^Furnished deliverable:[ \t]*(views only|paused)[ \t]*\r?$", brief, re.I | re.M):
            continue
        if not current_camera:
            actions.append(f"{room.name}: review the furnished camera for {revision}")
            continue
        for stage, action in (("products", "check the visible product variants and finishes"),
                              ("final-ai", "make and compare the final photo with its checked camera"),
                              ("handover", "verify and issue the room pack with the final photo")):
            row = stages.get(stage, {})
            purchase_only = stage == "products" and row.get("status") == "hold" and row.get("hold_scope") == "purchase"
            if row.get("status") == "hold" and not purchase_only:
                actions.append(f"{room.name}: resolve {stage} hold: {row.get('finding') or action}")
                break
            if (row.get("status") != "pass" and not purchase_only) or row.get("revision") != revision:
                actions.append(f"{room.name}: {action} for {revision}")
                break
        else:
            if outputs is not None:
                verify_room_pack(outputs, room, revision, stages, photo_quality=True)
            if completed is not None:
                completed.append(room.name)
    return actions


def save(root, revision, *, change, why, author, affects, next_step, question=None,
         question_image=None, image_description=None, question_kind=None):
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
    fields = decision_fields(out, question, question_kind, question_image, image_description)
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
            receipt = local_path(draft, "decision-preview.json")
            if receipt.is_file():
                pending = stored_json(receipt)
                if pending.pop("revision") != revision or (fields and pending != fields):
                    raise ValueError("The handover differs from the question already presented.")
                fields = pending
                fields["question_purpose"] = "study"
            from tools.check_delivery import verify_issue
            verify_issue(stage / "outputs")
            brochure_folders = {path.parent for path in (stage / "outputs").rglob("*")
                                if path.name in ("Comparison.pdf", "Visual-uses.json", "existing.html", "proposed.html")
                                and any((path.parent / other).is_file() for other in ("existing.html", "proposed.html",
                                        "Comparison.pdf", "Visual-uses.json") if other != path.name)}
            if brochure_folders:
                from tools.comparison_visuals import verify_saved
                for folder in sorted(brochure_folders):
                    verify_saved(root, folder, records=stage / "inputs")
            if base.get("pack_request"):
                import house_delivery
                details["pack_issue"] = house_delivery.release_check(root, base, stage, draft)
            import house_photos
            house_photos.exterior_review(root, stage / "outputs", revision,
                                         house_photos.exterior_register(root).get(revision, {}))
            combined = stage / "outputs" / house_photos.ARCHIVE
            if combined.exists():
                house_photos.verify_assembly(root, combined)
            remaining = furnished_actions(root, revision, base["parent"], stage / "outputs")
            scope_invitation = fields.get("question_kind") == "scope" and not answer_path(root, revision).is_file()
            if remaining and fields and (not receipt.is_file() or scope_invitation):
                raise ValueError("Continue the agreed furnished room before asking what is next. "
                                 + " | ".join(remaining) + ". Save a checkpoint without --ask, "
                                 "or use ask for a decision needed to proceed.")
            visual = fields.get("question_image")
            if visual and hashes.get(visual["path"]) != visual["sha256"]:
                raise ValueError("The question image changed after validation. Preserve the original image.")
            details.update(fields)
            saved = datetime.now(timezone.utc)
            house_id = stored_json(root / "project.json")["id"]
            filename = f"{house_id}/{revision}-{saved:%Y%m%dT%H%M%S%fZ}.zip"
            archive = backup_directory() / safe_relative(filename)
            record = dict(version=1, decision_format=1, delivery_format=5, house=house_id, toolkit=toolkit_checkout(), backup=filename,
                          saved=saved.isoformat(), **base, **details, outputs=hashes)
            write_json(stage / "record.json", record)
            final.parent.mkdir(exist_ok=True)
            backup(root, archive, Path(__file__).resolve().parent, staged_revision=stage)
            try:
                publish_directory(stage, final)
            except OSError as exc:
                raise OSError(f"Backup verified at {archive}, but publishing {final} failed: {exc}") from exc
    import house_checklist
    house_checklist.try_refresh(root)
    return final


def records(root):
    folder = local_path(root, HISTORY)
    if not folder.exists():
        return []
    return sorted((stored_json(local_path(root, path.relative_to(root).as_posix()))
                   for path in folder.glob("*/record.json")), key=lambda item: (item["saved"], item["revision"]))


def homeowner_question(record):
    return record.get("question") or "Would you like to take that next step, choose a different priority or pause here?"


def question_prompt(root, record, *, draft=False):
    visual = record.get("question_image")
    if not visual:
        if record.get("question_kind") == "visual":
            raise ValueError("Visual decision is missing its checked image.")
        return homeowner_question(record)
    parent = local_path(root, f"{WORK}/{record['revision']}") if draft else record_dir(root, record["revision"])
    image = local_path(parent, "outputs/" + visual["path"])
    if not image.is_file():
        raise ValueError(f"Decision image missing. Recover {record['revision']}/outputs/{visual['path']} before presenting the question.")
    with image.open("rb") as stream:
        if transfer(stream) != visual["sha256"]:
            raise ValueError(f"Decision image changed. Recover the checked {record['revision']} image before presenting the question.")
    alt = " ".join(visual["description"].split()).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    target = image.resolve().as_posix().replace("%", "%25").replace("<", "%3C").replace(">", "%3E")
    return f"![{alt}](<{target}>)\n\n{visual['description']}\n\n{homeowner_question(record)}"


def answer_path(root, revision):
    return local_path(root, f"handover-answers/{revision_id(revision)}.json")


def record_answer(root, revision, reply):
    revision = revision_id(revision)
    answer = reply.strip()
    if not answer:
        raise ValueError("Supply the homeowner's actual reply.")
    target = answer_path(root, revision)
    work = local_path(root, WORK)
    work.mkdir(exist_ok=True)
    with _save_lock(work):
        saved = local_path(record_dir(root, revision), "record.json") if record_dir(root, revision).is_dir() else None
        record = stored_json(saved or local_path(root, f"{WORK}/{revision}/decision-preview.json"))
        if target.is_file():
            if stored_json(target)["answer"] != answer:
                raise ValueError("This handover already has a reply. Record a changed instruction as a new dated decision.")
            return target
        target.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work, prefix=".staging-answer-") as temp:
            staged = Path(temp) / "reply.json"
            write_json(staged, dict(revision=record["revision"], date=datetime.now(timezone.utc).isoformat(),
                                    question=record.get("question"), answer=answer))
            staged.rename(target)
    return target


def next_choice(root, saved, revision=None, *, suggest=True):
    drafts = []
    for name in open_drafts(root):
        receipt = local_path(root, f"{WORK}/{name}/decision-preview.json")
        if receipt.is_file():
            drafts.append(stored_json(receipt))
    if revision:
        record = next((r for r in drafts if r["revision"] == revision_id(revision)), None)
        if record is None:
            record = stored_json(local_path(record_dir(root, revision), "record.json"))
    elif saved or drafts:
        # An internal save should neither bury an open choice nor repeat one already answered.
        choices = list(reversed(drafts)) + [r for r in reversed(saved) if r.get("question") or answer_path(root, r["revision"]).is_file()]
        record = next((r for r in choices if not answer_path(root, r["revision"]).is_file()),
                      choices[0] if choices else saved[-1])
        if not choices and not suggest:
            return ""
    else:
        return "Which space or household routine would you like to review first?" if suggest else ""
    answered = answer_path(root, record["revision"]).is_file()
    if record not in drafts and (record.get("question_purpose") != "study" or answered):
        current = record if revision or not saved else saved[-1]
        completed = []
        remaining = furnished_actions(root, current["revision"], current.get("parent"), completed=completed)
        # A real outstanding decision from another study still has an owner.
        if remaining and (not record.get("question") or answered or
                          (record == current and record.get("question_kind") == "scope")):
            return "Continue the agreed furnished room: " + " | ".join(remaining)
        if completed and not revision and answered and record != current:
            record = current
    answer = answer_path(root, record["revision"])
    if answer.is_file():
        return f"Homeowner reply ({record['revision']}): {stored_json(answer)['answer']}"
    if record in drafts:
        return question_prompt(root, record, draft=True)
    action = f"Next step ({record['revision']}): {record['next_step']}"
    if record.get("decision_format") and not record.get("question"):
        return action
    return f"{action}\n{question_prompt(root, record)}"


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
        if record.get("question"):
            lines.append(f"Homeowner question at handover: {record['question']}")
        if record.get("question_image"):
            lines.append(f"Decision image: {record['question_image']['path']} | {record['question_image']['description']}")
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
