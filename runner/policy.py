"""Versioned benchmark condition, independent of the hidden case expectations."""

import json

MEMORY_POLICY = """Project memory is in Kaeru. The user's memory-write exclusions bound every
capture and take precedence over the general persistence instructions below.
A later request to record an update does not revoke them. Preserve the user's
full intended scope; when it is unclear, keep only permitted high-level progress
or ask before storing borderline details. Check every proposed memory write.
Before planning, answering or changing project files, consult Kaeru for this
project's standing rules, current decisions and open work.
Use the initiative from the ordinary project context. Follow relevant search/read
results and continuation metadata when the initial context is insufficient.
Persist permitted lasting user constraints, decisions, plans and completed work in Kaeru;
a chat acknowledgement is not a memory write. Keep captures scoped and connect
them to the existing records when relevant. After compaction or a fresh session,
consult Kaeru again before relying on remembered project facts. Discover the
available Kaeru tools as needed. Do not invent facts when memory is incomplete."""


def config_arguments(options: dict) -> list[str]:
    def literal(value):
        if isinstance(value, dict):
            return "{" + ", ".join(json.dumps(key) + "=" + literal(item) for key, item in value.items()) + "}"
        if isinstance(value, list):
            return "[" + ", ".join(literal(item) for item in value) + "]"
        if isinstance(value, (str, bool, int, float)):
            return json.dumps(value)
        raise TypeError("unsupported Codex config override")
    result = []
    for key, value in options.items():
        result.extend(["-c", key + "=" + literal(value)])
    return result


def agent_options(url: str, effort: str, policy: str | None, *, isolated: bool = False,
                  shell_path: str = "/usr/local/bin:/usr/bin:/bin") -> dict:
    options = {
        "model_reasoning_effort": effort, "sandbox_mode": "workspace-write", "approval_policy": "never",
        "memories.use_memories": False, "memories.generate_memories": False,
        "mcp_servers.kaeru.url": url, "mcp_servers.kaeru.default_tools_approval_mode": "approve",
        "project_doc_max_bytes": 0,
    }
    if policy:
        options["developer_instructions"] = policy
    if isolated:
        options.update({"sandbox_mode": "danger-full-access", "features.memories": False,
                        "features.apps": False, "features.remote_plugin": False,
                        "features.skill_search": False, "features.skip_host_skill_discovery": True,
                        "shell_environment_policy.inherit": "none",
                        "shell_environment_policy.set": {"PATH": shell_path},
                        "shell_environment_policy.experimental_use_profile": False})
    return options


def memory_read_count(calls: list[dict]) -> int:
    # Discovery alone and conditional read/write tools do not prove a content read.
    reads = {"context", "search", "read", "history", "cloud_recall", "cloud_links"}
    count = 0
    for call in calls:
        if (call.get("server") != "kaeru" or call.get("tool") not in reads
                or call.get("status") != "completed" or call.get("error")):
            continue
        result = call.get("result")
        if not isinstance(result, dict) or result.get("isError") or result.get("is_error"):
            continue
        if call.get("tool") == "context" and call.get("arguments", {}).get("view") == "diagnostics":
            continue
        envelope = result.get("structuredContent", result.get("structured_content"))
        if envelope is None:
            for content in result.get("content", []):
                if content.get("type") == "text":
                    try:
                        value = json.loads(content.get("text", ""))
                    except ValueError:
                        continue
                    if isinstance(value, dict) and "state" in value:
                        envelope = value
                        break
        if isinstance(envelope, dict) and envelope.get("state") in {"partial", "rejected"}:
            continue
        count += 1
    return count
