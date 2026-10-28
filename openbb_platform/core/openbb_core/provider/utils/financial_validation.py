"""Explicit query/result validation boundaries for financial provider adapters."""

from typing import TypeVar

from openbb_core.provider.utils.financial_errors import (
    FinancialError,
    FinancialErrorCode,
)
from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


def _validate(
    model: type[Model], payload: object, code: FinancialErrorCode, provider: str | None
) -> Model:
    try:
        return model.model_validate(payload)
    except ValidationError:
        # Raise after leaving the handler so Pydantic inputs cannot survive as context.
        pass
    raise FinancialError(code, provider=provider) from None


def validate_financial_query(
    model: type[Model], payload: object, *, provider: str | None = None
) -> Model:
    """Validate query models before provider I/O without retaining supplied inputs."""
    return _validate(model, payload, FinancialErrorCode.INVALID_PARAMETERS, provider)


def validate_financial_result(
    model: type[Model], payload: object, *, provider: str | None = None
) -> Model:
    """Validate provider result rows separately from caller parameter errors."""
    return _validate(model, payload, FinancialErrorCode.INVALID_RESPONSE, provider)
