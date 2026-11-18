"""Bounded FMP dividends; retained FMP 1.6.1 declarations and aliases.

Provider LICENSE and provenance inventory retain the upstream license notice.
Source member SHA256 88dd04a6d4945b655a824e8f3c7d38f3cfd506a2243dfc9fb2ab7c97842eb12b.
"""

import re
from datetime import date as dateType
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
from openbb_core.provider.standard_models.historical_dividends import (
    HistoricalDividendsData,
    HistoricalDividendsQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition


def _civil(value):
    if value is None or type(value) is dateType:
        return value
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Civil date required")
    return dateType.fromisoformat(value)


class FMPHistoricalDividendsQueryParams(HistoricalDividendsQueryParams):
    """One listing, one bounded upstream page, optional local ex-date filters."""

    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", max_rows=100),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(min_length=1, max_length=50)
    start_date: dateType | None = None
    end_date: dateType | None = None
    limit: int = Field(default=20, ge=1, le=100, strict=True)

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Admit a scalar provider listing without URL syntax."""
        if type(value) is not str or not re.fullmatch(
            r"[A-Za-z0-9^][A-Za-z0-9.^=-]{0,49}", value
        ):
            raise ValueError("One listing required")
        return value.upper()

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def civil_dates(cls, value):
        """Reject timestamp and numeric calendar coercions."""
        return _civil(value)

    @model_validator(mode="before")
    @classmethod
    def explicit_null(cls, value):
        """Omitted filters differ from explicit null inputs."""
        if isinstance(value, dict) and any(v is None for v in value.values()):
            raise ValueError("Explicit null is not omission")
        return value

    @model_validator(mode="after")
    def ordered(self):
        """Local ex-date bounds are inclusive and ordered."""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Ordered dates required")
        return self


def _template(name):
    numeric = name in ("amount", "adjusted_amount", "dividend_yield")
    return FinancialFieldTemplate(
        unit=("ratio" if name == "dividend_yield" else "currency_per_share")
        if numeric
        else None,
        scale=1 if numeric else None,
        value_origin="provider_calculation"
        if name == "dividend_yield"
        else "provider_observation",
        observation_date_field="ex_dividend_date",
    )


class FMPHistoricalDividendsData(HistoricalDividendsData):
    """Separate cash amounts and civil event dates without inferred currency."""

    model_config = ConfigDict(allow_inf_nan=False)
    __alias_dict__ = {
        "ex_dividend_date": "date",
        "amount": "dividend",
        "adjusted_amount": "adjDividend",
        "dividend_yield": "yield",
        "record_date": "recordDate",
        "payment_date": "paymentDate",
        "declaration_date": "declarationDate",
    }
    symbol: str = Field(description="Exact company listing identity.")
    ex_dividend_date: dateType = Field(
        validation_alias="date",
        serialization_alias="ex_dividend_date",
        description="The ex-dividend date - the date on which the stock begins trading without rights to the dividend.",
    )
    amount: float = Field(
        validation_alias="dividend",
        serialization_alias="amount",
        description="The dividend amount per share.",
    )
    declaration_date: dateType | None = Field(
        None,
        validation_alias="declarationDate",
        serialization_alias="declaration_date",
        description="Declaration date of the historical dividends.",
    )
    record_date: dateType | None = Field(
        None,
        validation_alias="recordDate",
        serialization_alias="record_date",
        description="Record date of the historical dividends.",
    )
    payment_date: dateType | None = Field(
        None,
        validation_alias="paymentDate",
        serialization_alias="payment_date",
        description="Payment date of the historical dividends.",
    )
    adjusted_amount: float | None = Field(
        None,
        validation_alias="adjDividend",
        serialization_alias="adjusted_amount",
        description="Provider adjusted cash dividend per share; adjustment methodology unknown.",
    )
    dividend_yield: float | None = Field(
        None,
        validation_alias="yield",
        serialization_alias="dividend_yield",
        description="Dividend yield represented by the payment.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    frequency: str | None = Field(None, description="Frequency of the payment.")
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _template(name)
                for name in (
                    "symbol",
                    "ex_dividend_date",
                    "amount",
                    "declaration_date",
                    "record_date",
                    "payment_date",
                    "adjusted_amount",
                    "dividend_yield",
                    "frequency",
                )
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator(
        "ex_dividend_date",
        "declaration_date",
        "record_date",
        "payment_date",
        mode="before",
    )
    @classmethod
    def dates(cls, value):
        """Blank optional provider dates represent absent dates."""
        return _civil(None if value == "" else value)

    @field_validator("amount", "adjusted_amount", "dividend_yield", mode="before")
    @classmethod
    def numbers(cls, value):
        """Reject boolean and string amounts rather than coercing observations."""
        if value is not None and type(value) not in (int, float):
            raise ValueError("Numeric observation required")
        return value

    @field_validator("dividend_yield", mode="before")
    @classmethod
    def normalize_percent(cls, value):
        """Source percentage points convert to ratio, including zero."""
        if value is not None and type(value) not in (int, float):
            raise ValueError("Numeric yield required")
        return value / 100 if value is not None else None


def _row(query, raw):
    if not isinstance(raw, dict):
        raise FinancialError("invalid_response", provider="fmp")
    row = dict(raw)
    supplied = row.get("symbol", query.symbol)
    if type(supplied) is not str or supplied.upper() != query.symbol:
        raise FinancialError("invalid_response", provider="fmp")
    row["symbol"] = query.symbol
    return validate_financial_result(FMPHistoricalDividendsData, row, provider="fmp")


class FMPHistoricalDividendsFetcher(
    Fetcher[FMPHistoricalDividendsQueryParams, list[FMPHistoricalDividendsData]]
):
    """One acquisition; validation precedes defensive clipping and local filtering."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPHistoricalDividendsQueryParams:
        """Return credential-free typed query errors."""
        return validate_financial_query(
            FMPHistoricalDividendsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the accepted safe transport without retries or pagination."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {
            "symbol": query.symbol,
            "limit": query.limit,
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data_many(
            "https://financialmodelingprep.com/stable/dividends?" + urlencode(params),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPHistoricalDividendsData]]:
        """Preserve source order and duplicate event dates."""
        validated = [_row(query, raw) for raw in data.payload]
        clipped = validated[: query.limit]
        rows = [
            row
            for row in clipped
            if (query.start_date is None or row.ex_dividend_date >= query.start_date)
            and (query.end_date is None or row.ex_dividend_date <= query.end_date)
        ]
        return AnnotatedResult(
            result=rows,
            metadata=_metadata(
                query, rows, data, len(validated) > query.limit
            ).as_metadata(),
        )


def _metadata(query, rows, data, truncated):
    fields = render_field_templates(FMPHistoricalDividendsData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/fundamental/dividends",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="dividends",
            documentation="https://site.financialmodelingprep.com/developer/docs",
        ),
        effective_query=query.model_dump(mode="json"),
        fields=fields,
        observation_date_field="ex_dividend_date",
        bounds=FinancialBounds(
            requested_limit=query.limit,
            effective_limit=query.limit,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Upstream limit applies before local inclusive ex-dividend date filtering; history completeness is unknown.",
            "Currency, adjustment methodology, yield price basis and annualization are unknown.",
            "Separate civil event dates have no inferred timezone or point-in-time availability.",
            "Product caps do not assert provider maxima or account entitlement.",
        ],
    )
