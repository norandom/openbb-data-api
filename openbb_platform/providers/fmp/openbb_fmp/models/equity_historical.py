"""Bounded daily FMP observations; no interpolation or local price adjustment."""

import re
from datetime import date as dateType
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_historical import (
    EquityHistoricalData,
    EquityHistoricalQueryParams,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
    ProceduralBounds,
    ResponsePolicy,
    bind_query_annotation,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
    FinancialTransformation,
)
from openbb_core.provider.utils.financial_errors import (
    FinancialError,
    FinancialErrorCode,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPEquityHistoricalQueryParams(EquityHistoricalQueryParams):
    """One symbol, mandatory ordered dates and at most five calendar years."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        procedural_bounds=ProceduralBounds(max_calendar_years=5),
        response_policy=ResponsePolicy(mode="clip", max_rows=5000),
        runtime_properties=["bounds", "effective_query", "retrieved_at"],
    )

    start_date: dateType
    end_date: dateType
    interval: Literal["1d"] = "1d"
    adjustment: Literal["splits_only"] = "splits_only"

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Reject multi-symbol and URL syntax before uppercase normalization."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("One symbol required")
        if not re.fullmatch(r"[A-Za-z0-9^][A-Za-z0-9.^_/-]{0,49}", value.strip()):
            raise ValueError("One symbol required")
        return value.strip().upper()

    @model_validator(mode="after")
    def calendar_window(self):
        """Calendar anniversaries clamp leap day to February's last day."""
        years = bind_query_annotation(type(self)).procedural_bounds.max_calendar_years
        if not self.start_date <= self.end_date <= self.start_date + relativedelta(years=years):
            raise ValueError("Dates must be ordered within five calendar years")
        return self


class FMPEquityHistoricalData(EquityHistoricalData):
    """Nullable observations retain the full endpoint's split-adjusted price basis."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "date": FinancialFieldTemplate(
                period_basis="daily", observation_date_field="date", effective_frequency="daily",
                value_origin="provider_observation",
            ),
            "open": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_observation",
            ),
            "high": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_observation",
            ),
            "low": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_observation",
            ),
            "close": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_observation",
            ),
            "volume": FinancialFieldTemplate(
                unit="shares", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_observation",
            ),
            "vwap": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_calculation",
            ),
            "change": FinancialFieldTemplate(
                unit="currency/share", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="provider_calculation",
            ),
            "change_percent": FinancialFieldTemplate(
                unit="fraction", scale=1, period_basis="daily", observation_date_field="date",
                effective_frequency="daily", value_origin="locally_derived",
            ),
        },
        runtime_properties=["fields.availability"],
    )

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    date: dateType = Field(description="Provider daily observation.")
    open: float | None = Field(default=None, description="Provider split-adjusted opening price.")
    high: float | None = Field(default=None, description="Provider split-adjusted daily high.")
    low: float | None = Field(default=None, description="Provider split-adjusted daily low.")
    close: float | None = Field(default=None, description="Provider split-adjusted closing price.")
    change: float | None = Field(default=None, description="Provider price change from previous close.")
    change_percent: float | None = Field(
        default=None, description="Provider percentage-point change divided by 100 to a fraction.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )

    @field_validator("change_percent", mode="after")
    @classmethod
    def percent_fraction(cls, value):
        """Zero percentage change is an observation, not a missing value."""
        return None if value is None else value / 100


class FMPEquityHistoricalFetcher(
    Fetcher[FMPEquityHistoricalQueryParams, list[FMPEquityHistoricalData]]
):
    """Acquire one bounded daily history through the typed FMP transport."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEquityHistoricalQueryParams:
        """Safe validation does not change the caller's date or symbol inputs."""
        return validate_financial_query(FMPEquityHistoricalQueryParams, dict(params), provider="fmp")

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Preserve transport classification and actual acquisition time."""
        from openbb_fmp.utils.helpers import get_data_many  # pylint: disable=import-outside-toplevel

        params = {"symbol": query.symbol, "from": query.start_date.isoformat(),
                  "to": query.end_date.isoformat(),
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        url = "https://financialmodelingprep.com/stable/historical-price-eod/full?" + urlencode(params)
        return await get_data_many(url, with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPEquityHistoricalData]]:
        """Stable ascending order keeps duplicate dates in provider order."""
        if not isinstance(data.payload, list):
            raise FinancialError(FinancialErrorCode.INVALID_RESPONSE, provider="fmp")
        if not data.payload:
            raise FinancialError(FinancialErrorCode.MISSING_DATA, provider="fmp")
        rows = [validate_financial_result(FMPEquityHistoricalData, item, provider="fmp")
                for item in data.payload]
        if any(not query.start_date <= item.date <= query.end_date for item in rows):
            raise FinancialError(FinancialErrorCode.INVALID_RESPONSE, provider="fmp")
        rows.sort(key=lambda item: item.date)
        observed = len(rows)
        rows = rows[:bind_query_annotation(type(query)).response_policy.max_rows]
        return AnnotatedResult(result=rows, metadata=_metadata(query, rows, data, observed).as_metadata())


def _fields(rows):
    """Currency and corporate-action implementation details remain unavailable."""
    fields = render_field_templates(FMPEquityHistoricalData)
    for name, field in fields.items():
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    return fields


def _metadata(query, rows, data, observed):
    """Clipping is observed; absence of clipping cannot prove complete coverage."""
    limit = bind_query_annotation(type(query)).response_policy.max_rows
    clipped = observed > limit
    return FinancialResultMetadata(
        dataset="equity/price/historical", provider="fmp", retrieved_at=data.retrieved_at,
        source=FinancialSource(endpoint="historical-price-eod/full"), fields=_fields(rows),
        effective_query={"symbol": query.symbol, "start_date": query.start_date.isoformat(),
                         "end_date": query.end_date.isoformat(), "interval": query.interval,
                         "adjustment": query.adjustment},
        bounds=FinancialBounds(effective_limit=limit, returned_count=len(rows),
                               truncated=True if clipped else None,
                               completeness="partial" if clipped else "unknown"),
        observation_date_field="date",
        transformations=[FinancialTransformation(
            name="percentage_points_to_fraction", affected_fields=["change_percent"],
            source_basis="Provider changePercent in percentage points.",
            definition="change_percent = changePercent / 100; null remains null.",
        )],
        limitations=[
            "Full-endpoint OHLC uses the provider split-adjusted convention; no local adjustment is applied.",
            "Dividend adjustment is unsupported; corporate-action implementation and currency are unknown.",
            "Ascending dates retain duplicate observations in provider order, counting toward the 5000-row cap.",
            "Missing trading dates are not filled; historical completeness and publication dates are unknown.",
        ],
    )
