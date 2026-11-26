"""Resolve a visual placement against the house's design decision and derivative review."""
from datetime import date
import csv
import hashlib
import json
from pathlib import Path

import house_revisions as revisions

REGISTERS = ("design-states.json", "visual-approvals.json")
NATIVE = {".fcstd", ".blend", ".ifc", ".dwg", ".dxf", ".step", ".stp", ".brep", ".scad", ".py", ".json"}


def signature(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def arrangement_signature(state):
    """The decision binds the arrangement and editable geometry independently of any visual."""
    return signature({k: state[k] for k in ("phase", "revision", "scopes", "arrangement", "exclusions", "geometry", "features")})


def checksum(path):
    with path.open("rb") as stream:
        return revisions.transfer(stream)


def words(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Visual release requires {key}")
    return value


def strings(record, key, *, empty=False):
    values = record.get(key)
    if (not isinstance(values, list) or (not empty and not values)
            or any(not isinstance(v, str) or not v.strip() for v in values) or len(set(values)) != len(values)):
        raise ValueError(f"Visual release requires a distinct list for {key}")
    return values


class Catalogue:
    def __init__(self, root, records=None, *, design_only=False):
        self.root = Path(root)
        self.house = revisions.stored_json(self.root / "project.json")["id"]
        self.states = self.register(records or self.root, REGISTERS[0], "states")
        self.visuals = {} if design_only else self.register(records or self.root, REGISTERS[1], "visuals")
        self.old_states = self.superseded(self.states)
        self.old_visuals = self.superseded(self.visuals)
        self.hashes = {}
        self.defects = {}
        for path in (self.root / "rooms").glob("*/photo-defects.csv"):
            with path.open(encoding="utf-8-sig", newline="") as stream:
                self.defects.update((r["photo_sha256"], r["finding"]) for r in csv.DictReader(stream))

    def register(self, directory, name, key):
        path = revisions.local_path(directory, name)
        if not path.is_file():
            raise ValueError(f"Missing {name}. Record the design basis and purpose-specific visual review before issue.")
        data = revisions.stored_json(path)
        if data.get("version") != 1 or data.get("house") != self.house or not isinstance(data.get(key), dict):
            raise ValueError(f"{name}: different house or invalid register")
        return data[key]

    @staticmethod
    def superseded(records):
        old = set()
        for key, rec in records.items():
            if not isinstance(rec, dict):
                raise ValueError(f"Invalid approval record {key}")
            targets = strings(rec, "supersedes", empty=True)
            if key in targets or set(targets) - records.keys():
                raise ValueError(f"{key}: invalid supersession")
            old.update(targets)
        return old

    def evidence(self, ref, *, published=False):
        name = words(ref, "path")
        digest = words(ref, "sha256")
        path = revisions.local_path(self.root, name)
        if revisions.safe_relative(name).parts[0] == revisions.WORK or not path.is_file():
            raise ValueError(f"Missing saved design evidence: {name}")
        if name not in self.hashes:
            self.hashes[name] = checksum(path)
        if self.hashes[name] != digest:
            raise ValueError(f"Stale or changed design evidence: {name}")
        if published or "revision" in ref:
            rev = revisions.revision_id(words(ref, "revision"))
            prefix = f"revisions/{rev}/outputs/"
            if not name.startswith(prefix):
                raise ValueError(f"{name}: expected a saved output of {rev}")
            record = revisions.stored_json(revisions.record_dir(self.root, rev) / "record.json")
            if (record.get("house") != self.house or record.get("revision") != rev
                    or record.get("outputs", {}).get(name[len(prefix):]) != digest):
                raise ValueError(f"{name}: source revision or saved digest differs")
        return path

    def design(self, key, phase, scope, *, accepted):
        state = self.states.get(key)
        if not state or key in self.old_states:
            raise ValueError(f"{key}: missing or superseded design state")
        scopes = strings(state, "scopes")
        if scope not in scopes or state.get("phase") != phase:
            raise ValueError(f"{key}: design state does not cover {phase} {scope}")
        status = state.get("status")
        if (phase not in ("existing", "proposed") or
                (phase == "existing" and status != "observed") or
                (phase == "proposed" and status not in (("accepted",) if accepted else ("accepted", "for-review")))):
            raise ValueError(f"{key}: design status {status} cannot support this placement")
        # Concurrent alternatives for review can coexist. A current accepted arrangement is unambiguous.
        if status == "accepted" and any(other != key and other not in self.old_states and
                item.get("status") == "accepted" and item.get("phase") == phase and scope in item.get("scopes", [])
                for other, item in self.states.items()):
            raise ValueError(f"{scope}: resolve competing accepted states by recording supersession")
        words(state, "arrangement")
        strings(state, "exclusions", empty=True)
        revision = words(state, "revision")
        geometry = state.get("geometry")
        if not isinstance(geometry, list) or not geometry:
            raise ValueError(f"{key}: missing geometry or survey basis")
        if not any(ref.get("revision") == revision for ref in geometry):
            raise ValueError(f"{key}: geometry does not identify the state revision {revision}")
        for ref in geometry:
            path = self.evidence(ref, published=True)
            if phase == "proposed" and path.suffix.lower() not in NATIVE:
                raise ValueError(f"{key}: a proposed state requires editable native geometry")
        if status == "accepted":
            decision = state.get("homeowner_decision") or {}
            if decision.get("kind") != "design-acceptance":
                raise ValueError(f"{key}: link the homeowner's explicit design acceptance")
            words(decision, "by")
            date.fromisoformat(words(decision, "date")[:10])
            quote = words(decision, "quote")
            evidence = self.evidence(decision)
            if evidence.suffix.lower() == ".json":
                answer = revisions.stored_json(evidence)
                if quote != answer.get("answer") or answer.get("revision") != decision.get("decision_revision"):
                    raise ValueError(f"{key}: homeowner reply or decision revision differs")
            elif quote not in evidence.read_text(encoding="utf-8-sig"):
                raise ValueError(f"{key}: recorded homeowner acceptance wording is missing")
            binding = revisions.stored_json(self.evidence(decision.get("binding", {})))
            if binding != {"house": self.house, "state": key, "kind": "design-acceptance",
                           "arrangement_sha256": arrangement_signature(state), "decision_sha256": decision["sha256"],
                           "by": decision["by"], "date": decision["date"], "quote": quote}:
                raise ValueError(f"{key}: arrangement, scope or decision differs from the accepted record")
        features = state.get("features")
        if not isinstance(features, dict):
            raise ValueError(f"{key}: declare the consequential feature inventory")
        for feature, item in features.items():
            words(item, "description")
            if (set(strings(item, "scopes")) - set(scopes) or
                    set(strings(item, "required_views")) - {"plan", "section"}):
                raise ValueError(f"{key}/{feature}: invalid feature scope or required view")
        return state

    def approve(self, *, purpose, phase, scope, view, page=1, path=None, visual_id=None, accepted=False):
        """The caller supplies the destination's purpose and scope independently of the approval."""
        if type(page) is not int or page < 1:
            raise ValueError("Visual source pages start at one")
        grant = {"purpose": purpose, "scope": scope}
        if visual_id is None:
            rel = path.relative_to(self.root).as_posix()
            matches = [k for k, v in self.visuals.items() if k not in self.old_visuals
                       and v.get("source", {}).get("path") == rel and v.get("page", 1) == page
                       and grant in v.get("placements", []) and v.get("view") == view]
            if len(matches) != 1:
                raise ValueError(f"{rel}: require one signed visual for {purpose}, {scope}, page {page}")
            visual_id, = matches
        visual = self.visuals.get(visual_id)
        if not visual or visual_id in self.old_visuals or visual.get("status") != "signed":
            raise ValueError(f"{visual_id}: missing, superseded or unsigned visual")
        if (grant not in visual.get("placements", []) or visual.get("view") != view
                or visual.get("page", 1) != page):
            raise ValueError(f"{visual_id}: not approved for {purpose}, {scope}, {view}, page {page}")
        words(visual, "reviewer")
        strings(visual, "limitations", empty=True)
        state_id = words(visual, "state")
        state = self.design(state_id, phase, scope,
                            accepted=accepted or purpose.startswith(("comparison.", "photo-pack.")))
        if visual.get("state_sha256") != signature(state):
            raise ValueError(f"{visual_id}: design changed after visual review")
        canonical = self.evidence(visual["source"], published=True)
        if visual["source"]["sha256"] in self.defects:
            raise ValueError(f"{visual_id}: reported photo defect: {self.defects[visual['source']['sha256']]}")
        if path is not None and path != canonical and checksum(path) != visual["source"]["sha256"]:
            raise ValueError(f"{visual_id}: staged pixels differ from approved source")
        dependencies = visual.get("dependencies")
        if not isinstance(dependencies, list):
            raise ValueError(f"{visual_id}: record the derivative's design dependencies")
        for ref in dependencies:
            self.evidence(ref)
        observations = visual.get("features", {})
        expected = {}
        camera_view = view in ("camera", "photo")
        if camera_view and state["features"]:
            framing = revisions.stored_json(self.evidence(visual.get("framing", {})))
            if (framing.get("state_sha256") != signature(state) or framing.get("camera") != words(visual, "camera")
                    or framing.get("basis") not in ("native-camera", "survey-photo")):
                raise ValueError(f"{visual_id}: stale or mismatched camera visibility review")
            self.evidence(framing.get("reference", {}))
            expected = framing.get("features", {})
            for feature in state["features"]:
                if expected.get(feature) not in ("visible", "outside-frame", "obscured"):
                    raise ValueError(f"{visual_id}: missing camera visibility for {feature}")
        for feature, item in state["features"].items():
            if not camera_view and scope not in item["scopes"]:
                continue
            if view not in (*item["required_views"], "camera", "photo"):
                continue
            check = observations.get(feature, {})
            allowed = ("shown", "outside-frame", "obscured") if view in ("camera", "photo") else ("shown",)
            if check.get("visibility") not in allowed:
                raise ValueError(f"{visual_id}: account for {feature} in this {view}")
            if feature in expected and check["visibility"] != {"visible": "shown"}.get(expected[feature], expected[feature]):
                raise ValueError(f"{visual_id}: {feature} differs from the reviewed camera visibility")
            words(check, "finding")
            self.evidence(check.get("evidence", {}))
        return {"id": visual_id, "purpose": purpose, "scope": scope, "view": view, "page": page,
                "state_id": state_id, "design": state, "approval": visual}

    def coverage(self, proofs, scopes, *, phases):
        """A combined design issue must account for independently declared plans and sections."""
        for key, state in self.states.items():
            if key in self.old_states or state.get("phase") not in phases or state.get("status") == "for-review":
                continue
            relevant_state = scopes.intersection(state.get("scopes", []))
            if relevant_state:
                self.design(key, state["phase"], next(iter(relevant_state)), accepted=True)
            for feature, row in state.get("features", {}).items():
                relevant = set(row["scopes"]) & scopes
                if not relevant:
                    continue
                for view in row["required_views"]:
                    if not any(p["state_id"] == key and p["scope"] in relevant and p["view"] == view
                               and p["approval"]["features"].get(feature, {}).get("visibility") == "shown" for p in proofs):
                        raise ValueError(f"{key}: missing reviewed {view} showing {feature}")


def checked_placement(live, frozen, **kwargs):
    proof = live.approve(**kwargs)
    if frozen.approve(**kwargs) != proof:
        raise ValueError(f"{proof['id']}: placement approval changed after the commission was frozen")
    return proof
