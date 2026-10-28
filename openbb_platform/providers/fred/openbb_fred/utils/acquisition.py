"""Retain the successful network acquisition time across FRED cache paths."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

CacheState = Literal["network", "memory", "disk", "coalesced"]


@dataclass(frozen=True)
class FredAcquisition:
    """Payload provenance; retrieval time is never the time of a cache read."""

    payload: Any
    retrieved_at: datetime
    cache_state: CacheState

    def __post_init__(self) -> None:
        """Reject unknown freshness rather than manufacturing an acquisition."""
        if not isinstance(self.retrieved_at, datetime) or self.retrieved_at.utcoffset() is None:
            raise ValueError("FRED acquisition requires a timezone-aware retrieval time")
        if self.cache_state not in ("network", "memory", "disk", "coalesced"):
            raise ValueError("Unknown FRED acquisition cache state")
        object.__setattr__(self, "retrieved_at", self.retrieved_at.astimezone(timezone.utc))


def disk_record(value: Any) -> dict:
    """Version payloads without assigning retrieval times to raw legacy callers."""
    acquisition = isinstance(value, FredAcquisition)
    return {
        "version": 1,
        "payload": value.payload if acquisition else value,
        "retrieved_at": value.retrieved_at.isoformat() if acquisition else None,
    }


def from_disk_record(record: Any) -> FredAcquisition | None:
    """Treat unknown, malformed and legacy provenance as a cache miss."""
    if not isinstance(record, dict) or record.get("version") != 1:
        return None
    if "payload" not in record or not isinstance(record.get("retrieved_at"), str):
        return None
    try:
        return FredAcquisition(
            record["payload"], datetime.fromisoformat(record["retrieved_at"]), "disk"
        )
    except (TypeError, ValueError):
        return None
