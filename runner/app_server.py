"""Owned stdio connection; notifications are buffered even before an RPC ack."""

from collections import deque
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

from .io import clean_kaeru_env
from .process import stop


class AppServer:
    def __init__(self, command: list[str], workspace: Path, output: Path):
        self.trace = output / "compaction-events.jsonl"
        self.trace.open("x").close()
        self.stderr = (output / "compaction.stderr").open("x")
        self.process = None
        self.sequence = 0
        self.incoming = queue.Queue()
        self.notifications = deque()
        try:
            self.process = subprocess.Popen(command, cwd=workspace, env=clean_kaeru_env(),
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
                                            text=True, bufsize=1, start_new_session=True)
        except BaseException:
            self.stderr.close()
            raise
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.incoming.put(line)
        finally:
            self.incoming.put(None)

    def _record(self, direction, message):
        with self.trace.open("a") as stream:
            stream.write(json.dumps({"direction": direction, "message": message}, ensure_ascii=False) + "\n")

    def send(self, message: dict):
        self._record("request", message)
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def _next(self, deadline: float) -> dict:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("app-server deadline expired")
        try:
            line = self.incoming.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError("app-server response timed out") from None
        if line is None:
            raise RuntimeError("app-server closed stdout")
        try:
            message = json.loads(line)
        except ValueError:
            self._record("invalid_response", {"line": line})
            raise RuntimeError("app-server sent malformed JSON") from None
        if not isinstance(message, dict):
            raise RuntimeError("app-server sent a non-object message")
        self._record("response", message)
        if "method" in message and "id" in message:
            self.send({"id": message["id"], "error": {"code": -32601,
                       "message": "Benchmark compaction client does not execute server requests"}})
            raise RuntimeError("unexpected app-server request during compaction")
        return message

    def request(self, method: str, params: dict, deadline: float) -> dict:
        self.sequence += 1
        ident = self.sequence
        self.send({"id": ident, "method": method, "params": params})
        while True:
            message = self._next(deadline)
            if message.get("id") == ident and "method" not in message:
                if "error" in message:
                    raise RuntimeError(f"app-server rejected {method}: {message['error'].get('code')}")
                if "result" not in message:
                    raise RuntimeError("app-server response has no result")
                return message["result"]
            if "method" not in message:
                raise RuntimeError("unexpected app-server response id")
            self.notifications.append(message)

    def notification(self, deadline: float) -> dict:
        if self.notifications:
            return self.notifications.popleft()
        message = self._next(deadline)
        if "method" not in message:
            raise RuntimeError("unexpected response while waiting for compaction")
        return message

    def close(self):
        if self.process:
            stop(self.process)
            self.reader.join(timeout=1)
            self.process.stdin.close()
            self.process.stdout.close()
        self.stderr.close()
