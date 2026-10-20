"""R2 catalogue and result handling over a host-owned MCP session.

The injected request function accepts (method, params) and returns the MCP
result object. The host owns initialization, authentication and transport errors.
"""

from collections.abc import Callable
from copy import deepcopy
import json
from typing import Any

from jsonschema import validators
from jsonschema.exceptions import SchemaError, ValidationError

from .models import ToolReply


class ProtocolError(RuntimeError):
    """The peer did not satisfy the advertised R2 contract."""


class OperationFailed(RuntimeError):
    def __init__(self, reply: ToolReply, previous_pages: tuple[ToolReply, ...]):
        super().__init__(f"{reply.operation} did not complete successfully")
        self.reply = reply
        self.previous_pages = previous_pages


class R2Client:
    def __init__(self, request: Callable[[str, dict[str, Any]], dict[str, Any]]):
        self.request = request
        self.tools: dict[str, dict[str, Any]] = {}

    def discover(self, *, max_pages: int = 32) -> dict[str, dict[str, Any]]:
        """Load the live catalogue; never translate legacy tool names."""
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        tools: dict[str, dict[str, Any]] = {}
        cursors: set[str] = set()
        arguments: dict[str, Any] = {}
        for _ in range(max_pages):
            result = self.request("tools/list", arguments)
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                raise ProtocolError("tools/list must return a tools array")
            for tool in result["tools"]:
                if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                    raise ProtocolError("invalid tool definition")
                name = tool["name"]
                if not name or name in tools:
                    raise ProtocolError("empty or duplicate tool name")
                for key in ("inputSchema", "outputSchema"):
                    if key == "outputSchema" and key not in tool:
                        continue  # Cloud tools retain their text contracts.
                    schema = tool.get(key)
                    if not isinstance(schema, dict):
                        raise ProtocolError(f"{name}: missing or invalid {key}")
                    try:
                        validators.validator_for(schema).check_schema(schema)
                    except SchemaError as exc:
                        raise ProtocolError(f"{name}: invalid {key}") from exc
                tools[name] = deepcopy(tool)
            cursor = result.get("nextCursor")
            if cursor is None:
                self.tools = tools
                return deepcopy(tools)
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise ProtocolError("invalid or repeated tools/list cursor")
            cursors.add(cursor)
            arguments = {"cursor": cursor}
        raise ProtocolError("tools/list page limit exceeded")

    def call(self, operation: str, arguments: dict[str, Any]) -> ToolReply:
        """Issue exactly one call, retaining partial/rejected responses as evidence."""
        if operation not in self.tools:
            raise ProtocolError(f"tool not discovered: {operation}")
        definition = self.tools[operation]
        self._validate(definition["inputSchema"], arguments, operation, "arguments")
        raw = self.request(
            "tools/call", {"name": operation, "arguments": deepcopy(arguments)}
        )
        if not isinstance(raw, dict):
            raise ProtocolError("tools/call must return an object")
        if "isError" in raw and not isinstance(raw["isError"], bool):
            raise ProtocolError("isError must be a boolean")
        content = raw.get("content")
        if not isinstance(content, list):
            raise ProtocolError("tools/call must return a content array")
        envelope = None
        if "outputSchema" in definition:
            text = [item.get("text") for item in content
                    if isinstance(item, dict) and item.get("type") == "text"]
            envelope = raw.get("structuredContent")
            if envelope is None:
                if len(text) != 1 or not isinstance(text[0], str):
                    raise ProtocolError("local result needs structured content or one JSON text")
                try:
                    envelope = json.loads(text[0])
                except ValueError as exc:
                    raise ProtocolError("local text result is not JSON") from exc
            elif text:
                try:
                    matches = len(text) == 1 and json.loads(text[0]) == envelope
                except (ValueError, TypeError):
                    matches = False
                if not matches:
                    raise ProtocolError("structured and text results disagree")
            self._validate(definition["outputSchema"], envelope, operation, "result")
            if (not isinstance(envelope, dict) or type(envelope.get("api_version")) is not int
                    or envelope["api_version"] != 1 or envelope.get("operation") != operation):
                raise ProtocolError("unexpected API version or operation")
            if envelope.get("state") not in {"ok", "applied", "unchanged", "partial", "rejected"}:
                raise ProtocolError("unknown operation state")
        return ToolReply(operation, deepcopy(raw), deepcopy(envelope))

    def read_pages(
        self, operation: str, arguments: dict[str, Any], *, max_pages: int = 128
    ) -> tuple[ToolReply, ...]:
        """Explicit audit helper, never automatic expansion for the tested agent.

        Pages remain separate. A final page may still report incomplete coverage;
        exhausting a continuation is not proof of an exhaustive search.
        """
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        definition = self.tools.get(operation, {})
        if (not definition.get("annotations", {}).get("readOnlyHint")
                or "outputSchema" not in definition):
            raise ProtocolError("pagination requires a discovered local read operation")
        pages: list[ToolReply] = []
        current = deepcopy(arguments)
        cursors = {current["cursor"]} if isinstance(current.get("cursor"), str) else set()
        for _ in range(max_pages):
            reply = self.call(operation, current)
            if not reply.successful:
                raise OperationFailed(reply, tuple(pages))
            pages.append(reply)
            continuation = reply.envelope.get("continuation")
            if continuation is None:
                return tuple(pages)
            if not isinstance(continuation, dict):
                raise ProtocolError("invalid continuation")
            cursor = continuation.get("cursor")
            current = continuation.get("next_arguments")
            if (not isinstance(cursor, str) or not cursor or cursor in cursors
                    or not isinstance(current, dict) or current.get("cursor") != cursor):
                raise ProtocolError("invalid or repeated continuation cursor")
            cursors.add(cursor)
            current = deepcopy(current)
        raise ProtocolError("read page limit exceeded")

    @staticmethod
    def _validate(schema: dict, value: Any, operation: str, label: str) -> None:
        try:
            validators.validator_for(schema)(schema).validate(value)
        except ValidationError:
            # Do not copy bodies, arguments or credentials into exception messages.
            raise ProtocolError(f"{operation}: {label} violates advertised schema") from None
