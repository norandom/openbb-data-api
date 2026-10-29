"""Sanitized FRED failures: remote bodies and signed URLs are never diagnostics."""
from typing import Any

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.utils.financial_errors import FinancialError


def validate_response(payload: Any, status: int | None = None) -> None:
    """Classify failures without retaining signed URLs or remote error bodies."""
    code = str(status or (payload.get("error_code") if isinstance(payload, dict) else ""))
    message = str(payload.get("error_message", "")) if isinstance(payload, dict) else ""
    if code in {"401", "403"} or (code == "400" and any(
        word in message.lower() for word in ("api_key", "api key", "auth", "key")
    )):
        raise OpenBBError("FRED authentication failed.")
    if code == "404" or "does not exist" in message.lower():
        raise OpenBBError("FRED data unavailable.")
    if message or (code.isdigit() and int(code) >= 400):
        raise OpenBBError("FRED request failed.")


def observations(payload: Any) -> list[dict]:
    """Reject unavailable series while preserving published missing observations."""
    validate_response(payload)
    rows = payload.get("observations") if isinstance(payload, dict) else None
    if not rows:
        raise OpenBBError("FRED data unavailable.")
    return rows


def safe_error(error: OpenBBError) -> FinancialError:
    """Keep known failure categories and suppress arbitrary transport diagnostics."""
    if type(error) is FinancialError:
        return FinancialError(
            error.code, provider="fred", retry_after_seconds=error.retry_after_seconds,
        )
    categories = {
        "FRED authentication failed.": "authentication",
        "FRED data unavailable.": "missing_data",
        "FRED API rate limit exceeded (HTTP 429). Please wait a moment and try again.": "throttling",
    }
    return FinancialError(categories.get(str(error), "upstream"), provider="fred")
