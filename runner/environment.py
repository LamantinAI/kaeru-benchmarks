"""Disposable native MCP and optional cloud processes, never an existing daemon."""

import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import uuid
from urllib.parse import quote

from .io import clean_kaeru_env, write_json
from .process import stop
from .transport import Session


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class Environment:
    def __init__(self, binary: Path, vault: Path, output: Path, *, cloud_binary: Path | None = None):
        self.binary, self.vault, self.output, self.cloud_binary = binary, vault, output, cloud_binary
        self.processes = []
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}/mcp"
        self.env = clean_kaeru_env()
        config = output / "clouds.toml"
        config.write_text("")
        self.env.update(KAERU_VAULT_PATH=str(vault), KAERU_MCP_LISTEN_ADDRESS="127.0.0.1",
                        KAERU_MCP_LISTEN_PORT=str(self.port), KAERU_MCP_CLOUDS_FILE=str(config),
                        KAERU_MCP_HYGIENE_ENABLE="0", KAERU_MCP_UPDATE_CHECK="0",
                        KAERU_MCP_VIZ_ENABLE="0", KAERU_READ_TRACE_ENABLED="false",
                        KAERU_MCP_UI_ENABLE="0", KAERU_MCP_WEB_CONFIG_FILE=str(output / "browser-account.toml"))
        self.artifact_root = output / "observer-exports"
        self.artifact_root.mkdir()
        self.env["KAERU_MCP_ARTIFACT_ROOT"] = str(self.artifact_root)

    def _start(self, binary: Path, env: dict, label: str):
        with (self.output / f"{label}.log").open("w") as log:
            process = subprocess.Popen([str(binary)], env=env, stdout=log, stderr=log,
                                       start_new_session=True)
        self.processes.append(process)
        return process

    def start(self, manifest: dict) -> Session:
        try:
            if manifest["cloud_nodes"]:
                self._cloud(manifest)
            process = self._start(self.binary, self.env, "mcp")
            session = Session(self.url, self.output / "audit-mcp.jsonl")
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("disposable MCP stopped; see mcp.log")
                try:
                    self.initialization = session.initialize()
                    write_json(self.output / "initialize.json", self.initialization)
                    return session
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(.1)
            raise TimeoutError("disposable MCP startup timeout")
        except BaseException:
            self.close()
            raise

    def _cloud(self, manifest: dict) -> None:
        if self.cloud_binary is None:
            raise ValueError("Cloud fixtures require --cloud-binary for a disposable cloud")
        port, token = free_port(), uuid.uuid4().hex
        cloud = f"http://127.0.0.1:{port}"
        env = clean_kaeru_env()
        env.update(KAERU_VAULT_PATH=str(self.output / "cloud-vault"), KAERU_CLOUD_API_TOKEN=token,
                   KAERU_CLOUD_LISTEN_ADDRESS="127.0.0.1", KAERU_CLOUD_LISTEN_PORT=str(port),
                   KAERU_READ_TRACE_ENABLED="false")
        process = self._start(self.cloud_binary, env, "cloud")
        import urllib.request
        http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("disposable cloud stopped; see cloud.log")
            try:
                with http.open(urllib.request.Request(cloud + "/api/v1/initiatives", headers=headers), timeout=5):
                    break
            except urllib.error.URLError:
                time.sleep(.1)
        else:
            raise TimeoutError("disposable cloud startup timeout")
        for node in manifest["cloud_nodes"]:
            value = {"id": str(uuid.uuid4()), "name": node["name"], "body": node["body"],
                     "node_type": node.get("type", "reference"), "tier": node.get("tier", "archival"),
                     "layer": node.get("layer", "warm"), "initiative": manifest["initiative"]}
            request = urllib.request.Request(cloud + "/api/v1/nodes", json.dumps(value).encode(), headers)
            with http.open(request, timeout=10) as response:
                if response.status != 201:
                    raise RuntimeError("cloud seed rejected")
        listing = cloud + "/api/v1/initiatives/" + quote(manifest["initiative"], safe="") + "/nodes"
        with http.open(urllib.request.Request(listing, headers=headers), timeout=10) as response:
            briefs = json.load(response)
        write_json(self.output / "cloud-listing.json", briefs)
        if len(briefs) != len(manifest["cloud_nodes"]):
            raise ValueError("cloud seed count differs")
        readback = []
        for brief in briefs:
            request = urllib.request.Request(cloud + "/api/v1/nodes/" + quote(brief["id"], safe=""), headers=headers)
            with http.open(request, timeout=10) as response:
                readback.append(json.load(response))
        write_json(self.output / "cloud-readback.json", readback)
        by_name = {n["name"]: n for n in readback}
        for expected in manifest["cloud_nodes"]:
            actual = by_name.get(expected["name"], {})
            if (actual.get("body") != expected["body"]
                    or actual.get("node_type") != expected.get("type", "reference")):
                raise ValueError("cloud exact readback differs")
        config = self.output / "clouds.toml"
        config.write_text(f'[clouds.benchmark]\nurl={json.dumps(cloud)}\ntoken={json.dumps(token)}\n')
        config.chmod(0o600)
        # Keep synthetic credentials out of the published run manifest.
        write_json(self.output / "cloud-seed.json", {"nodes": manifest["cloud_nodes"],
                                                    "cloud": "benchmark", "disposable": True})

    def close(self) -> None:
        for process in reversed(self.processes):
            stop(process)
        self.processes.clear()
        (self.output / "clouds.toml").unlink(missing_ok=True)
