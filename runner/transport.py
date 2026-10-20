"""Small synchronous MCP session for host-side fixture audits only."""

import json
from pathlib import Path
import time
import urllib.request


class Session:
    def __init__(self, url: str, trace: Path, *, timeout: float = 30):
        self.url, self.trace, self.timeout = url, trace, timeout
        self.session_id = None
        self.version = "2025-06-18"
        self.sequence = 0
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def initialize(self) -> dict:
        result = self.request("initialize", {"protocolVersion": self.version, "capabilities": {},
                                             "clientInfo": {"name": "kaeru-bench-audit", "version": "1"}})
        self.version = result["protocolVersion"]
        self._exchange({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def request(self, method: str, params: dict) -> dict:
        self.sequence += 1
        response = self._exchange({"jsonrpc": "2.0", "id": self.sequence,
                                   "method": method, "params": params})
        if not isinstance(response, dict) or response.get("id") != self.sequence:
            raise RuntimeError("MCP response id mismatch")
        if "error" in response:
            raise RuntimeError(f"MCP protocol error: {response['error'].get('code')}")
        return response["result"]

    def _record(self, direction: str, value: dict) -> None:
        with self.trace.open("a") as stream:
            stream.write(json.dumps({"direction": direction, "message": value}, ensure_ascii=False) + "\n")

    def _exchange(self, message: dict):
        self._record("request", message)
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers.update({"Mcp-Session-Id": self.session_id, "MCP-Protocol-Version": self.version})
        request = urllib.request.Request(self.url, json.dumps(message).encode(), headers)
        deadline = time.monotonic() + self.timeout
        with self.http.open(request, timeout=self.timeout) as response:
            self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
            if response.status == 202:
                return None
            if "text/event-stream" not in response.headers.get("Content-Type", ""):
                value = json.loads(response.read(8 * 1024 * 1024 + 1))
                self._record("response", value)
                return value
            data, size = [], 0
            while time.monotonic() < deadline:
                raw = response.readline(8 * 1024 * 1024 + 1)
                if not raw:
                    break
                size += len(raw)
                if size > 8 * 1024 * 1024:
                    raise RuntimeError("MCP reply exceeds audit byte limit")
                line = raw.decode().rstrip("\r\n")
                if line.startswith("data:"):
                    data.append(line[5:].lstrip())
                if not line and data:
                    payload, data = "\n".join(data), []
                    if not payload.strip():
                        continue
                    value = json.loads(payload)
                    self._record("response", value)
                    if value.get("id") == message.get("id"):
                        return value
        raise RuntimeError("MCP response missing or timed out")
