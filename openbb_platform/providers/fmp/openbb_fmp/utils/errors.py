"""Safe FMP failure categories; never retain provider bodies or request URLs."""

import re

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError
from openbb_core.provider.utils.financial_errors import FinancialError


class FMPError(OpenBBError):
    """Sanitized upstream or transport failure."""


class FMPUnauthorized(UnauthorizedError):
    """Sanitized authentication or subscription failure."""


class FMPEmptyData(EmptyDataError):
    """Explicit absence, preserved as HTTP 204 by the shared API."""


def fail(category: str, *, typed=False, retry_after=None):
    """Raise a safe message compatible with the shared core error pipeline."""
    safe = FinancialError(
        "upstream" if category in {"connection", "transport"} else category,
        provider="fmp",
        retry_after_seconds=retry_after,
    )
    if typed:
        raise safe
    message = f"FMP[{category}]: provider request failed."
    if category in {"authentication", "entitlement"}:
        error = FMPUnauthorized(message)
    elif category == "missing_data":
        error = FMPEmptyData(message)
    else:
        error = FMPError(message)
    for attribute in (
        "code",
        "provider",
        "retryable",
        "retry_after_seconds",
        "status_code",
    ):
        setattr(error, attribute, getattr(safe, attribute))
    raise error


def classify(status: int, message: str = "") -> str | None:
    """Prefer explicit protocol status; classify legacy HTTP-200 error envelopes."""
    codes = {
        401: "authentication",
        403: "entitlement",
        429: "throttling",
        400: "invalid_parameters",
        422: "invalid_parameters",
        404: "missing_data",
    }
    if status in codes:
        return codes[status]
    if status != 200:
        return "upstream"
    # Echoed request URLs carry credentials and query terms, not failure semantics.
    lowered = re.sub(r"https?://[^\s]+", "", message.lower())
    groups = (
        ("throttling", ("limit reach", "rate limit", "too many requests")),
        (
            "authentication",
            (
                "invalid api key",
                "invalid apikey",
                "missing api key",
                "missing apikey",
                "api key is invalid",
                "invalid credentials",
                "unauthorized",
            ),
        ),
        (
            "entitlement",
            (
                "upgrade",
                "subscription",
                "premium",
                "exclusive endpoint",
                "special endpoint",
                "restricted endpoint",
            ),
        ),
        ("missing_data", ("no data", "not found", "no results")),
        ("invalid_parameters", ("invalid", "parameter", "symbol")),
    )
    for category, patterns in groups:
        if any(pattern in lowered for pattern in patterns):
            return category
    return "upstream" if message else None
