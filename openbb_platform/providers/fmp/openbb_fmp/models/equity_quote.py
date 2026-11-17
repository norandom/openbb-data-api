"""FMP quotes preserve listing identity and independently dated financial facts."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# 8329b1cdcc92ed4794b925640081ae34e093a71979503577fe65b486e813cfef.
import re
from datetime import UTC, datetime
from math import isfinite
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_quote import (
    EquityQuoteData,
    EquityQuoteQueryParams,
)
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
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPEquityQuoteQueryParams(EquityQuoteQueryParams):
    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="provider"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        description="One provider listing identity; maximum 50 characters.",
        max_length=50,
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Reject ambiguous identities and query syntax before normalization."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("One symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("One symbol is required")
        return value


def _template(name):
    """Quote time does not establish market-cap or share-count measurement time."""
    prices = {
        "bid",
        "ask",
        "last_price",
        "open",
        "high",
        "low",
        "close",
        "prev_close",
        "change",
        "year_high",
        "year_low",
        "ma50",
        "ma200",
    }
    unit = "currency/share" if name in prices else None
    if name in {"volume", "exchange_volume", "last_size"}:
        unit = "shares"
    elif name in {"bid_size", "ask_size"}:
        unit = "round_lots"
    elif name == "sequence_number":
        unit = "count"
    elif name == "market_cap":
        unit = "currency"
    elif name == "change_percent":
        unit = "ratio"
    return FinancialFieldTemplate(
        unit=unit,
        scale=1 if unit else None,
        value_origin="provider_calculation"
        if name in {"market_cap", "change", "change_percent", "ma50", "ma200"}
        else "provider_observation",
        observation_date_field="last_timestamp"
        if name in {"last_price", "last_timestamp", "change", "change_percent"}
        else None,
        period_basis="order size in round lots; standard describes normal lot as 100 shares, actual listing lot convention unverified"
        if unit == "round_lots"
        else None,
        source_unit="percent" if name == "change_percent" else None,
        requested_transform="divide_by_100" if name == "change_percent" else None,
        financial_basis={"market_date": None, "share_count": None},
    )


class FMPEquityQuoteData(EquityQuoteData):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    __alias_dict__ = {
        "ma50": "priceAvg50",
        "ma200": "priceAvg200",
        "last_timestamp": "timestamp",
        "high": "dayHigh",
        "low": "dayLow",
        "last_price": "price",
        "change_percent": "changePercentage",
        "prev_close": "previousClose",
    }
    ma50: float | None = Field(default=None, description="50 day moving average price.")
    ma200: float | None = Field(
        default=None, description="200 day moving average price."
    )
    market_cap: float | None = Field(
        default=None, description="Market cap of the company."
    )
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _template(name)
                for name in [
                    *EquityQuoteData.model_fields,
                    "ma50",
                    "ma200",
                    "market_cap",
                ]
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("*", mode="wrap")
    @classmethod
    def safe_field(cls, value, handler):
        """Contain inherited integer conversion errors before public error projection."""
        try:
            result = handler(value)
        except (TypeError, ValueError, OverflowError, OSError):
            pass
        else:
            if not isinstance(result, float) or isfinite(result):
                return result
        raise ValueError("Invalid financial result field")

    @field_validator(
        "bid",
        "ask",
        "bid_size",
        "ask_size",
        "last_price",
        "last_size",
        "sequence_number",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "exchange_volume",
        "prev_close",
        "change",
        "change_percent",
        "year_high",
        "year_low",
        "ma50",
        "ma200",
        "market_cap",
        mode="before",
    )
    @classmethod
    def numeric_fact(cls, value):
        """Financial amounts cannot be booleans or structured values."""
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float, str))
        ):
            raise ValueError("Numeric source fact required")
        return value

    @field_validator("last_timestamp", mode="before")
    @classmethod
    def unix_timestamp(cls, value):
        """Provider timestamp is Unix seconds; retain zero and fractional precision."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError("Unix seconds required")
        try:
            return datetime.fromtimestamp(float(value), UTC)
        except (TypeError, ValueError, OverflowError, OSError):
            raise ValueError("Invalid Unix seconds") from None

    @field_validator(
        "participant_timestamp", "trf_timestamp", "sip_timestamp", mode="before"
    )
    @classmethod
    def source_timestamp(cls, value):
        """Only the documented last timestamp has a Unix conversion contract."""
        if value is not None and not isinstance(value, datetime):
            if not isinstance(value, str) or not re.match(
                r"^\d{4}-\d{2}-\d{2}[Tt ]", value
            ):
                raise ValueError("ISO timestamp required")
        return value

    @field_validator("change_percent", mode="after")
    @classmethod
    def normalize_percent(cls, value):
        """Normalize the provider percentage without changing absolute price change."""
        return value / 100 if value is not None else None


class FMPEquityQuoteFetcher(
    Fetcher[FMPEquityQuoteQueryParams, list[FMPEquityQuoteData]]
):
    """Acquire one quote response without retries, fan-out or substitute values."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEquityQuoteQueryParams:
        return validate_financial_query(
            FMPEquityQuoteQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        from openbb_fmp.utils.helpers import get_data_many

        params = {
            "symbol": query.symbol,
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data_many(
            "https://financialmodelingprep.com/stable/quote?" + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any):
        rows = [
            validate_financial_result(FMPEquityQuoteData, row, provider="fmp")
            for row in data.payload
        ]
        if len(rows) > 1 or any(row.symbol != query.symbol for row in rows):
            raise FinancialError("invalid_response", provider="fmp") from None
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data).as_metadata()
        )


def _metadata(query, rows, data):
    fields = render_field_templates(FMPEquityQuoteData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/price/quote",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="quote",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/quote",
        ),
        effective_query=query.model_dump(),
        fields=fields,
        observation_date_field="last_timestamp",
        bounds=FinancialBounds(returned_count=len(rows), completeness="unknown"),
        limitations=[
            "Prices retain currency/share units with currency unknown; no currency is inferred.",
            "Last timestamp is Unix seconds in UTC; it dates the quote, not market cap or share counts.",
            "Market-cap calculation methodology, share-count basis and measurement dates are unknown.",
            "Publication/vintage and restatements are unknown; this is not point-in-time safe.",
            "Bid, ask, OHLC and previous close retain separate provider meanings without substitution.",
            "changePercentage is divided by 100; absolute price change is retained independently.",
        ],
    )
