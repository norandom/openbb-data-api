"""Typed public financial failures without upstream payloads or credentials."""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from math import ceil
from uuid import uuid4

from openbb_core.app.model.abstract.error import OpenBBError


class FinancialErrorCode(StrEnum):
    """Stable categories shared by adapters and public error handlers."""

    AUTHENTICATION = "authentication"
    ENTITLEMENT = "entitlement"
    THROTTLING = "throttling"
    TIMEOUT = "timeout"
    INVALID_PARAMETERS = "invalid_parameters"
    INVALID_RESPONSE = "invalid_response"
    MISSING_DATA = "missing_data"
    UPSTREAM = "upstream"
    INTERNAL_ERROR = "internal_error"


# Preserve baseline HTTP compatibility; categories carry the finer distinction.
_POLICY = {
    FinancialErrorCode.AUTHENTICATION: (502, False, "Provider authentication failed."),
    FinancialErrorCode.ENTITLEMENT: (502, False, "Provider subscription access is required."),
    FinancialErrorCode.THROTTLING: (400, True, "Provider rate limit reached. Try again later."),
    FinancialErrorCode.TIMEOUT: (400, True, "Provider request timed out. Try again later."),
    FinancialErrorCode.INVALID_PARAMETERS: (422, False, "Invalid financial query parameters."),
    FinancialErrorCode.INVALID_RESPONSE: (502, False, "Provider returned invalid financial data."),
    FinancialErrorCode.MISSING_DATA: (204, False, "No financial data found."),
    FinancialErrorCode.UPSTREAM: (400, False, "Provider request failed."),
    FinancialErrorCode.INTERNAL_ERROR: (500, False, "Financial data request failed."),
}
_PROVIDERS = frozenset({"fmp", "fred", "yfinance"})
MAX_RETRY_AFTER_SECONDS = 86400
MAX_WRAPPER_DEPTH = 8


def parse_retry_after(value: object, *, now: datetime | None = None) -> int | None:
    """Accept bounded delta-seconds or HTTP dates without retaining header text."""
    if type(value) is str:
        if not value.isascii() or len(value) > 128:
            return None
        if value.isdecimal():
            if len(value) > 5:
                return None
            value = int(value)
        else:
            try:
                deadline = parsedate_to_datetime(value)
                clock = now if now is not None else datetime.now(UTC)
                if deadline.tzinfo is None or clock.tzinfo is None:
                    return None
                value = ceil((deadline - clock).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None
    if type(value) is not int or not 0 <= value <= MAX_RETRY_AFTER_SECONDS:
        return None
    return value


class FinancialError(OpenBBError):
    """Safe typed error; no caller-supplied message or upstream cause is stored."""

    def __init__(
        self,
        code: FinancialErrorCode | str,
        *,
        provider: str | None = None,
        retry_after_seconds: object = None,
    ):
        try:
            self.code = FinancialErrorCode(code)
        except (ValueError, TypeError):
            self.code = FinancialErrorCode.INTERNAL_ERROR
        self.status_code, self.retryable, self.detail = _POLICY[self.code]
        self.provider = provider if type(provider) is str and provider in _PROVIDERS else None
        self.retry_after_seconds = (
            parse_retry_after(retry_after_seconds) if self.retryable else None
        )
        self.correlation_id = (
            uuid4().hex if self.code == FinancialErrorCode.INTERNAL_ERROR else None
        )
        super().__init__(None)
        self.args = (self.detail,)

    def to_dict(self) -> dict:
        """Project only explicit safe attributes for API or Python consumers."""
        result = {
            "detail": self.detail,
            "code": self.code.value,
            "provider": self.provider,
            "retryable": self.retryable,
        }
        if self.retry_after_seconds is not None:
            result["retry_after_seconds"] = self.retry_after_seconds
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        return result


def normalize_financial_error(error: BaseException) -> FinancialError:
    """Unwrap only exact OpenBB wrappers; unknown exceptions fail closed."""
    current = error
    for _ in range(MAX_WRAPPER_DEPTH + 1):
        if type(current) is FinancialError:
            if current.__cause__ is None and current.__context__ is None:
                return current
            return FinancialError(
                current.code, provider=current.provider,
                retry_after_seconds=current.retry_after_seconds,
            )
        if type(current) is not OpenBBError:
            break
        current = current.original
    return FinancialError(FinancialErrorCode.INTERNAL_ERROR)
