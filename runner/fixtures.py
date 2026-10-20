"""Normalize declared fixtures and verify the actual disposable graph."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
import uuid

import yaml

from .workspaces import workspace_files


class InvalidFixture(ValueError):
    pass


def load_case(directory: Path) -> tuple[dict, dict]:
    case = yaml.safe_load((directory / "case.yaml").read_text())
    fixture = yaml.safe_load((directory / "fixture.yaml").read_text())
    if case["id"] != directory.name or not re.fullmatch(r"[A-Za-z0-9_-]+", case["id"]):
        raise InvalidFixture("case id must match its directory")
    return case, fixture


def select_cases(dataset: Path, selected: list[str] | None) -> list[Path]:
    cases = sorted(path for path in dataset.iterdir() if path.is_dir() and (path / "case.yaml").is_file())
    if selected:
        missing = set(selected) - {path.name for path in cases}
        if missing:
            raise ValueError("unknown case selection: " + ", ".join(sorted(missing)))
        cases = [path for path in cases if path.name in selected]
    if not cases:
        raise ValueError("no cases selected")
    return cases


def input_files(directory: Path, fixture: dict) -> set[Path]:
    files = {directory / "case.yaml", directory / "fixture.yaml"}
    if fixture.get("noise"):
        library = (directory / fixture["noise"]["library"]).resolve()
        if not library.is_relative_to(directory.parent.parent.resolve()):
            raise InvalidFixture("noise library must stay inside the dataset")
        files.add(library)
    files.update(source for source, _ in workspace_files(directory, fixture))
    return files


def normalize(directory: Path, fixture: dict, clock: datetime) -> dict:
    initiative = fixture["initiative"]
    case_id = directory.name
    now = int(clock.timestamp())
    noise_spec = fixture.get("noise", {})
    nodes = []
    def node(item, *, noise=False):
        init = item.get("initiative", initiative)
        if not isinstance(init, str) or not init:
            raise InvalidFixture("current fixtures require a named initiative")
        value = {"type": "episode", "tier": "operational", "layer": "warm", "body": "",
                 **item, "initiative": init, "noise": noise}
        value["tags"] = list(item.get("tags", []))
        if item.get("status") is not None:
            value["tags"].append("status:" + item["status"])
        recorded = item.get("recorded")
        if recorded is not None:
            seconds = int(datetime.combine(date.fromisoformat(str(recorded)),
                                          datetime.min.time(), timezone.utc).timestamp()) + 43200
        elif "recorded_order" in item:
            seconds = now - 10 + int(item["recorded_order"])
        elif noise and noise_spec.get("recorded_start"):
            start = datetime.fromisoformat(str(noise_spec["recorded_start"]).replace("Z", "+00:00"))
            if start.tzinfo is None:
                raise InvalidFixture("noise recorded_start needs a timezone")
            seconds = int(start.timestamp()) + len(nodes)
        else:
            seconds = now - 300 + len(nodes)
        value["recorded_epoch"] = seconds
        value["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"kaeru-bench:{case_id}:{init}:{item['name']}"))
        nodes.append(value)
    if fixture.get("noise"):
        noise = fixture["noise"]
        bank = yaml.safe_load((directory / noise["library"]).read_text())["nodes"]
        count = noise["count"]
        if not isinstance(count, int) or count < 0 or len(bank) < count:
            raise InvalidFixture("noise bank is smaller than declared")
        for item in bank[:count]:
            node(item, noise=True)
    for item in fixture.get("nodes", []):
        node(item)
    for item in fixture.get("tasks", []):
        tags = ["kind:task", "status:" + item.get("status", "open")]
        due = item.get("due")
        if due:
            match = re.fullmatch(r"([+-]\d+)([dw])", str(due))
            if match:
                due = (clock.date() + timedelta(days=int(match[1]) * (7 if match[2] == "w" else 1))).isoformat()
            else:
                due = date.fromisoformat(str(due)).isoformat()
            tags.append("due:" + due)
        node({**item, "type": "task", "tags": tags})
    for item in fixture.get("claims", []):
        node({**item, "type": "hypothesis", "status": item.get("verdict") or "open",
              "tags": ["kind:hypothesis"]})
    edges = list(fixture.get("edges", []))
    for review in fixture.get("reviews", []):
        name = "review-" + review["target"]
        node({"name": name, "body": review["reason"],
              "tags": ["kind:observation", "sig:high", "role:review"]})
        edges.append({"from": name, "to": review["target"], "type": "contradicts"})
    by_name = {n["name"]: n for n in nodes}
    if len(by_name) != len(nodes):
        raise InvalidFixture("duplicate fixture names need explicit disambiguation")
    normalized_edges = []
    for edge in edges:
        if edge["from"] not in by_name or edge["to"] not in by_name:
            raise InvalidFixture("edge endpoint missing from fixture")
        normalized_edges.append({**edge, "src": by_name[edge["from"]]["id"],
                                 "dst": by_name[edge["to"]]["id"], "weight": edge.get("weight", 1.0)})
    validation = None
    if noise_spec.get("target"):
        if not noise_spec.get("rank_probe"):
            raise InvalidFixture("search rank constraints require a declared rank_probe")
        validation = {"target": noise_spec["target"], "query": noise_spec["rank_probe"],
                      "rank_at_least": noise_spec["target_rank_at_least"],
                      "newer_noise_min": noise_spec.get("newer_noise_min", 1 if noise_spec.get("target_not_newest") else 0)}
    return {"case_id": case_id, "initiative": initiative, "clock_epoch": now, "nodes": nodes,
            "edges": normalized_edges, "policy": fixture.get("policy"),
            "search_validation": validation,
            "cloud_nodes": fixture.get("cloud_nodes", [])}


def verify_seed(manifest: dict, snapshot: dict) -> None:
    actual = {n["id"]: n for n in snapshot["graph"]["nodes"]}
    for expected in manifest["nodes"]:
        got = actual.get(expected["id"])
        if got is None:
            raise InvalidFixture("seeded node is not readable")
        for key in ("name", "body", "type", "tier", "layer", "tags"):
            a, b = got[key], expected[key]
            differs = sorted(a) != sorted(b) if key == "tags" else a != b
            if differs:
                raise InvalidFixture(f"seed readback differs: {key}")
        if got["initiatives"] != [expected["initiative"]] or got["created_secs"] != expected["recorded_epoch"]:
            raise InvalidFixture("seed scope or recorded time differs")
        if got.get("visibility") != "local":
            raise InvalidFixture("seed visibility differs")
    extras = [n for ident, n in actual.items() if ident not in {n["id"] for n in manifest["nodes"]}]
    if any(n["type"] != "board" for n in extras):
        raise InvalidFixture("unexpected extra seed content")
    expected_edges = {(e["src"], e["dst"], e["type"], e["weight"]) for e in manifest["edges"]}
    actual_edges = {(e["src"], e["dst"], e["type"], e["weight"]) for e in snapshot["graph"]["edges"]}
    if expected_edges != actual_edges:
        raise InvalidFixture("seed relationships differ")
