"""Bounded historical capitalization; retained FMP 1.6.1 model declarations.

License notice and recovery hashes: provider LICENSE and provenance.json.
Source member SHA256 e7ec73eca3471259207b5567f15d42b0d929d41c22bd7ed423f676c5818951ff.
"""

import re
from datetime import (
    UTC,
    date as dateType,
    datetime,
    timedelta,
)
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
    ProceduralBounds,
    ResponsePolicy,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.standard_models.historical_market_cap import (
    HistoricalMarketCapData,
    HistoricalMarketCapQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FmpHistoricalMarketCapQueryParams(HistoricalMarketCapQueryParams):  # noqa: D101

    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", max_rows=5000),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        max_length=50,
        description="One provider listing identity; maximum 50 characters.",
    )
    start_date: dateType | None = Field(
        default=None,
        description="ISO calendar date; omitted start resolves at acquisition to effective end minus 365 days. Ordered range at most 366 days.",
    )
    end_date: dateType | None = Field(
        default=None,
        description="ISO calendar date; omitted end resolves at acquisition to UTC today. Ordered range at most 366 days; fixed upstream limit 5000.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Override native coercion so malformed inputs fail before I/O."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("One symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("One symbol is required")
        return value

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def iso_calendar(cls, value):
        """Reject timestamp and numeric coercion of calendar dates."""
        if value is None or type(value) is dateType:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("ISO calendar date required")
        return dateType.fromisoformat(value)

    @model_validator(mode="after")
    def ordered_window(self):
        """Validate explicit bounds before the acquisition clock is consulted."""
        if self.start_date is not None and self.end_date is not None:
            _validate_window(self.start_date, self.end_date)
        return self


def _validate_window(start, end):
    if not 0 <= (end - start).days <= 366:
        raise ValueError("Ordered date window at most 366 days required")


def _resolve_dates(query):
    end = query.end_date or datetime.now(UTC).date()
    try:
        start = query.start_date or end - timedelta(days=365)
        _validate_window(start, end)
    except (ValueError, OverflowError):
        raise FinancialError("invalid_parameters", provider="fmp") from None
    return start, end


def _template(calculated=False):
    return FinancialFieldTemplate(
        unit="currency" if calculated else None,
        scale=1 if calculated else None,
        value_origin="provider_calculation" if calculated else "provider_observation",
        observation_date_field="date",
        financial_basis={
            "share_count": None,
            "market_date": "capitalization observation date; price basis unknown",
        },
    )


class FmpHistoricalMarketCapData(HistoricalMarketCapData):
    """FMP Historical Market Cap Data."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    __alias_dict__ = {"market_cap": "marketCap"}
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                "date": _template(),
                "symbol": _template(),
                "market_cap": _template(True),
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("market_cap", mode="before")
    @classmethod
    def numeric_capitalization(cls, value):
        """Keep zero distinct from missing values and reject boolean amounts."""
        if isinstance(value, bool):
            raise ValueError("Numeric capitalization required")
        return value

    @field_validator("date", mode="before")
    @classmethod
    def observation_date(cls, value):
        """Require an actual calendar observation date."""
        return FmpHistoricalMarketCapQueryParams.iso_calendar(value)


class FmpHistoricalMarketCapFetcher(
    Fetcher[FmpHistoricalMarketCapQueryParams, list[FmpHistoricalMarketCapData]]
):
    """Acquire one provider window without pagination or inferred financial facts."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FmpHistoricalMarketCapQueryParams:
        """Expose safe query failures without retaining caller inputs."""
        return validate_financial_query(
            FmpHistoricalMarketCapQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Send one encoded request and retain the shared helper receipt."""
        from openbb_fmp.utils.helpers import get_data_many

        start, end = _resolve_dates(query)
        # Persist the acquisition window so metadata cannot cross a UTC midnight.
        query.start_date, query.end_date = start, end
        params = {
            "symbol": query.symbol,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "limit": 5000,
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data_many(
            "https://financialmodelingprep.com/stable/historical-market-capitalization?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FmpHistoricalMarketCapData]]:
        """Validate every source row before clipping in provider order."""
        rows = [
            validate_financial_result(FmpHistoricalMarketCapData, row, provider="fmp")
            for row in data.payload
        ]
        truncated = len(rows) > 5000
        rows = rows[:5000]
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata()
        )


def _metadata(query, rows, data, truncated):
    start, end = _resolve_dates(query)
    fields = render_field_templates(FmpHistoricalMarketCapData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/historical_market_cap",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="historical-market-capitalization",
            documentation="https://site.financialmodelingprep.com/developer/docs",
        ),
        effective_query={
            "symbol": query.symbol,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        fields=fields,
        observation_date_field="date",
        bounds=FinancialBounds(
            requested_limit=5000,
            effective_limit=5000,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Capitalization is a provider calculation; currency, share count and price basis are unknown.",
            "Row date is the capitalization observation date, not publication or vintage time.",
            "Point-in-time availability and restatements are unknown; source row order is preserved.",
        ],
    )
