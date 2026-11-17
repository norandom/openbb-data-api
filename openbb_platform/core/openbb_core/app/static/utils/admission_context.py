"""Invocation-owned bridge between generated validation and Container execution."""

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import get_ident
from typing import Any

from openbb_core.app.model.abstract.error import OpenBBError


class InvalidParameters(OpenBBError):
    """Constant safe error for selected admission failures."""

    def __init__(self):
        super().__init__("invalid_parameters")


def owner():
    """Identify task as well as thread; copied child contexts are not owners."""
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return get_ident(), task


@dataclass
class AdmissionFrame:
    """Track pending, strict or baseline selection; clear raw values before sync_run."""

    container: Any
    route: str
    model: str
    query: type | None
    provider: str | None
    choice: Any
    priorities: tuple
    raw: dict
    controls: frozenset
    normalized: dict = field(default_factory=dict)
    kind: str = "strict"
    invocation: object = field(default_factory=object)
    owner: tuple = field(default_factory=owner)
    pinned: bool = False
    consumed: bool = False
    executing: bool = False


FRAME: ContextVar[AdmissionFrame | None] = ContextVar("openbb_admission", default=None)


def current_frame():
    """Return only the invocation owned by this execution context."""
    frame = FRAME.get()
    return frame if frame is not None and frame.owner == owner() else None


def matching_selection(container, choice, command, priorities):
    """Match the one generated resolver call before authoritative selection."""
    frame = current_frame()
    if frame is None:
        if FRAME.get() is not None:
            raise InvalidParameters() from None
        return None
    if (
        frame.container is not container
        or frame.route.strip("/").replace("/", ".") != command
        or frame.choice != choice
        or frame.priorities != tuple(priorities)
        or frame.pinned
        or frame.consumed
    ):
        raise InvalidParameters() from None
    frame.pinned = True
    return frame


def consume(container, route, provider=None):
    """Fail closed on invocation mismatch and repeated consumption."""
    frame = current_frame()
    if frame is None:
        if FRAME.get() is not None:
            raise InvalidParameters() from None
        return None
    if (
        frame.container is not container
        or frame.route != route
        or frame.consumed
        or not frame.pinned
        or provider != frame.provider
    ):
        raise InvalidParameters() from None
    frame.consumed = True
    return frame
