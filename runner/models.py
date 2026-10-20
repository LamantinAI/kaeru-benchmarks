"""Results retained by the benchmark without flattening API semantics."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolReply:
    operation: str
    raw: dict[str, Any]
    envelope: dict[str, Any] | None

    @property
    def successful(self) -> bool:
        return not self.raw.get("isError", False) and (
            self.envelope is None
            or self.envelope["state"] not in {"partial", "rejected"}
        )
