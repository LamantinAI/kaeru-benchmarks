"""Observer-only readbacks and snapshots, separate from evaluated tool traces."""

import hashlib
import json
from pathlib import Path

from .fixtures import InvalidFixture
from .io import write_json


def validate_search(client, manifest: dict, output: Path) -> None:
    validation = manifest.get("search_validation")
    if not validation:
        return
    pages = client.read_pages("search", {**validation["query"], "initiatives": [manifest["initiative"]]})
    hits = [node for page in pages for node in page.envelope["data"]["hits"]]
    names = [node["name"] for node in hits]
    target = next((n for n in manifest["nodes"] if n["name"] == validation["target"]), None)
    if target is None:
        raise InvalidFixture("declared search target is absent")
    rank = names.index(target["name"]) + 1 if target["name"] in names else 0
    newer = sum(n["noise"] and n["recorded_epoch"] > target["recorded_epoch"] for n in manifest["nodes"])
    write_json(output / "search-preflight.json", {"target_rank": rank, "newer_noise": newer,
                                                "responses": [p.raw for p in pages]})
    if (rank < validation["rank_at_least"] or newer < validation["newer_noise_min"]
            or not pages[-1].envelope["coverage"]["complete"]):
        raise InvalidFixture("declared search rank/age/exhaustion constraint failed")


def validate_cloud(client, manifest: dict, output: Path) -> None:
    if not manifest["cloud_nodes"]:
        return
    registry = client.call("clouds", {})
    known = registry.raw.get("structuredContent")
    if not isinstance(known, dict):
        texts = [item["text"] for item in registry.raw.get("content", []) if item.get("type") == "text"]
        known = json.loads(texts[0]) if len(texts) == 1 else {}
    if not registry.successful or known.get("clouds") != ["benchmark"]:
        raise InvalidFixture("only the disposable benchmark cloud may be configured")
    policy = client.call("policy", {"initiative": manifest["initiative"]})
    changes = policy.envelope.get("data", {}).get("changes", []) if policy.envelope else []
    if (not policy.successful or not any(c.get("field") == "policy" and c.get("after", {}).get("policy") == "team"
                                        for c in changes)):
        raise InvalidFixture("cloud initiative team policy was not recovered")
    write_json(output / "cloud-discovery.json", {"registry": registry.raw, "policy": policy.raw,
                                                "discovery": "native R2",
                                                "inline_context_advertisement": "not a fixture prerequisite in R2"})
    reply = client.call("cloud_recall", {"initiative": manifest["initiative"], "cloud": "benchmark"})
    if not reply.successful:
        raise InvalidFixture("cloud recall failed")
    content = "\n".join(item.get("text", "") for item in reply.raw["content"])
    if any(node["name"] not in content or node["body"].strip()[:40] not in content for node in manifest["cloud_nodes"]):
        raise InvalidFixture("cloud-only content is not recoverable")
    # Avoid context: it can mark reminders delivered before the tested agent.
    pages = client.read_pages("search", {"initiatives": [manifest["initiative"]],
                                         "filters": {"current": "all"}})
    local_names = {n["name"] for p in pages for n in p.envelope["data"]["hits"]}
    if local_names.intersection(n["name"] for n in manifest["cloud_nodes"]):
        raise InvalidFixture("cloud fixture leaked into the local vault")
    write_json(output / "cloud-preflight.json", {"local_cloud_separation": True, "recall": reply.raw})


def snapshot_api(client, artifact_root: Path, label: str, output: Path) -> None:
    initiatives = [name for page in client.read_pages("initiatives", {})
                   for name in page.envelope["data"]["initiatives"]]
    snapshots, records = [], []
    seen = set()
    for initiative in initiatives:
        destination = label + "-" + hashlib.sha256(initiative.encode()).hexdigest()[:12]
        reply = client.call("export", {"initiative": initiative, "destination": destination})
        if not reply.successful:
            raise RuntimeError("observer graph export failed")
        graph = json.loads((artifact_root / destination / "graph.json").read_text())
        snapshots.append({"initiative": initiative, "graph": graph})
        for node in graph["nodes"]:
            if node["id"] in seen:
                continue
            seen.add(node["id"])
            pages = client.read_pages("read", {"initiative": initiative, "node": node["id"]})
            records.append({"id": node["id"], "pages": [p.raw for p in pages]})
    write_json(output / f"{label}.memory.json", {"initiatives": snapshots, "records": records})
