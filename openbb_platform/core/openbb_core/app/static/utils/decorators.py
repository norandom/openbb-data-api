"""Decorators for the OpenBB Platform static assets."""

from collections.abc import Callable
from copy import deepcopy
from functools import wraps
from inspect import isawaitable, iscoroutinefunction
from typing import Any, TypeVar, overload

from pydantic import ValidationError, validate_call
from typing_extensions import ParamSpec

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.app.parameter_admission import select_frame, supplied
from openbb_core.app.static.utils.admission_context import (
    FRAME,
    InvalidParameters,
    owner,
)
from openbb_core.env import Env
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError

P = ParamSpec("P")
R = TypeVar("R")


@overload
def validate(func: Callable[P, R]) -> Callable[P, R]:
    pass  # pragma: no cover


@overload
def validate(**dec_kwargs) -> Callable[[Callable[P, R]], Callable[P, R]]:
    pass  # pragma: no cover


def validate(
    func: Callable[P, R] | None = None,
    **dec_kwargs,
) -> Any:
    """Validate function calls."""

    route = dec_kwargs.pop("_command_path", None)

    def decorated(f: Callable[P, R]):
        """Use for decorating functions."""

        def native(*args, **kwargs):
            return validate_call(f, **dec_kwargs)(*args, **kwargs)

        @wraps(f)
        def wrapper(*f_args, **f_kwargs):
            frame = select_frame(f, route, f_args, f_kwargs) if route else None
            if frame is None:
                return _ordinary_call(native, f_args, f_kwargs)
            if iscoroutinefunction(f):
                args = (f_args[0], *deepcopy(f_args[1:]))
                return _selected_async_call(frame, f, native, args, deepcopy(f_kwargs))
            return _selected_call(frame, f, native, f_args, f_kwargs)

        return wrapper

    return decorated if func is None else decorated(func)


def _ordinary_call(native, args, kwargs):
    """Isolate a nested baseline call from another invocation's frame."""
    outer = FRAME.get()
    token = FRAME.set(None)
    try:
        result = native(*args, **kwargs)
    finally:
        FRAME.reset(token)
    return (
        _ordinary_async(result) if outer is not None and isawaitable(result) else result
    )


async def _ordinary_async(result):
    """Keep a nested baseline await outside the caller's admission frame."""
    token = FRAME.set(None)
    try:
        return await result
    finally:
        FRAME.reset(token)


def _selected_call(frame, func, native, args, kwargs):
    """Keep selected raw admission alive through native validation and filtering."""
    token = FRAME.set(frame)
    try:
        if frame.kind == "strict":
            supplied(frame, func, args, kwargs)
        return native(*args, **kwargs)
    except Exception:
        if frame.kind != "strict" or frame.executing:
            raise
        raise InvalidParameters() from None
    finally:
        frame.raw.clear()
        frame.normalized.clear()
        FRAME.reset(token)


async def _selected_async_call(frame, func, native, args, kwargs):
    """Surround await with the selected lifecycle without changing baseline async calls."""
    frame.owner = owner()
    token = FRAME.set(frame)
    try:
        if frame.kind == "strict":
            supplied(frame, func, args, kwargs)
        return await native(*args, **kwargs)
    except Exception:
        if frame.kind != "strict" or frame.executing:
            raise
        raise InvalidParameters() from None
    finally:
        frame.raw.clear()
        frame.normalized.clear()
        FRAME.reset(token)


def exception_handler(func: Callable[P, R]) -> Callable[P, R]:
    """Handle exceptions, attempting to focus on the last call from the traceback."""

    @wraps(func)
    def wrapper(*f_args, **f_kwargs):
        try:
            return func(*f_args, **f_kwargs)
        except (ValidationError, OpenBBError, Exception) as e:
            if isinstance(e, InvalidParameters):
                raise
            if Env().DEBUG_MODE:
                raise

            # Get the last traceback object from the exception
            tb = e.__traceback__
            if tb:
                while tb.tb_next is not None:
                    tb = tb.tb_next

            if isinstance(e, ValidationError):
                error_list: list = []
                validation_error = f"{e.error_count()} validations error(s)"
                for err in e.errors(include_url=False):
                    loc = ".".join(
                        [
                            str(i)
                            for i in err.get("loc", ())
                            if i
                            not in (
                                "standard_params",
                                "extra_params",
                                "provider_choices",
                            )
                        ]
                    )
                    msg = err.get("msg", "")
                    _input = (
                        "..."
                        if msg == "Missing required argument"
                        else err.get("input", "")
                    )
                    prefix = f"[Data Model] {e.title}\n" if "Data" in e.title else ""
                    error_list.append(
                        f"{prefix}[Arg] {loc} -> input: {_input} -> {msg}"
                    )
                error_list.insert(0, validation_error)
                error_str = "\n".join(error_list)
                raise OpenBBError(f"\n[Error] -> {error_str}").with_traceback(
                    tb
                ) from None
            if isinstance(e, UnauthorizedError):
                raise UnauthorizedError(f"\n[Error] -> {e}").with_traceback(
                    tb
                ) from None
            if isinstance(e, EmptyDataError):
                raise EmptyDataError(f"\n[Empty] -> {e}").with_traceback(tb) from None
            if isinstance(e, OpenBBError):
                raise OpenBBError(f"\n[Error] -> {e}").with_traceback(tb) from None
            if isinstance(e, Exception):
                raise OpenBBError(
                    f"\n[Unexpected Error] -> {e.__class__.__name__} -> {e}"
                ).with_traceback(tb) from None

    return wrapper
