"""FMP market-wide dividend events with separate cash amounts and civil dates."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# caaedd4e33a107b5ba6328f6d74a386b3fb27d32b5d4fa9df5f1a61968d8935c.
import re
from datetime import date
from math import isfinite
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.calendar_dividend import (
    CalendarDividendData,
    CalendarDividendQueryParams,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
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
from pydantic import AliasGenerator, ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition, get_data

ENDPOINT = "dividends-calendar"
MAX_ROWS = 250
ALIASES = {
    "amount": "dividend",
    "ex_dividend_date": "date",
    "record_date": "recordDate",
    "payment_date": "paymentDate",
    "declaration_date": "declarationDate",
    "adjusted_amount": "adjDividend",
    "dividend_yield": "yield",
}


def _civil_date(value: Any) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("A civil date in YYYY-MM-DD format is required")


class FMPCalendarDividendQueryParams(CalendarDividendQueryParams):
    """Require one inclusive market-wide calendar window of up to seven days."""

    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            response_policy=ResponsePolicy(mode="clip", max_rows=MAX_ROWS),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    start_date: date
    end_date: date

    _date_input = field_validator("start_date", "end_date", mode="before")(_civil_date)

    @model_validator(mode="after")
    def window(self):
        """Reject inverted or oversized windows before acquisition."""
        if not 0 <= (self.end_date - self.start_date).days <= 6:
            raise ValueError("The inclusive window must span one to seven days")
        return self


def _field_template(name: str) -> FinancialFieldTemplate:
    source = ALIASES.get(name, name)
    if name == "dividend_yield":
        return FinancialFieldTemplate(
            source=source,
            source_unit="percentage_points",
            unit="ratio",
            scale=1,
            value_origin="provider_calculation",
        )
    units = {
        "ex_dividend_date": "civil_date",
        "record_date": "civil_date",
        "payment_date": "civil_date",
        "declaration_date": "civil_date",
        "amount": "currency_per_share",
        "adjusted_amount": "currency_per_share",
    }
    return FinancialFieldTemplate(
        source=source, unit=units.get(name), value_origin="provider_observation"
    )


class FMPCalendarDividendData(CalendarDividendData):
    """Preserve each date role, symbol and provider-supplied cash amount."""

    __alias_dict__ = ALIASES
    model_config = ConfigDict(
        allow_inf_nan=False,
        alias_generator=AliasGenerator(
            validation_alias=lambda name: ALIASES.get(name, name)
        ),
    )
    adjusted_amount: float | None = Field(
        default=None,
        description="Provider adjusted cash dividend per share; adjustment methodology unknown.",
    )
    dividend_yield: float | None = Field(
        default=None,
        description="Annualized dividend yield.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    frequency: str | None = Field(
        default=None, description="Frequency of the regular dividend payment."
    )

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _field_template(name)
                for name in (
                    *CalendarDividendData.model_fields,
                    "adjusted_amount",
                    "dividend_yield",
                    "frequency",
                )
            },
            runtime_properties=["fields.availability"],
        )
    )

    _event_date = field_validator("ex_dividend_date", mode="before")(_civil_date)

    @field_validator("record_date", "payment_date", "declaration_date", mode="before")
    @classmethod
    def optional_date(cls, value):
        """Represent a blank or absent optional date as unknown."""
        return None if value is None or value == "" else _civil_date(value)

    @field_validator("symbol")
    @classmethod
    def source_symbol(cls, value):
        """Attribute each market-wide event to its source listing."""
        if not value.strip():
            raise ValueError("A listing identity is required")
        return value

    @field_validator("amount", "adjusted_amount", "dividend_yield", mode="before")
    @classmethod
    def finite_numeric(cls, value, info):
        """Preserve null and zero, converting source yield percentage points to a ratio."""
        if value is None:
            return None
        if type(value) not in (float, int):
            raise ValueError("A finite numeric value is required")
        try:
            finite = isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("A finite numeric value is required")
        return value / 100 if info.field_name == "dividend_yield" else value


class FMPCalendarDividendFetcher(
    Fetcher[FMPCalendarDividendQueryParams, list[FMPCalendarDividendData]]
):
    """Acquire the admitted window once and cap the fully validated results."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCalendarDividendQueryParams:
        """Apply typed validation before preparing the upstream request."""
        return validate_financial_query(
            FMPCalendarDividendQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(
        query: FMPCalendarDividendQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Use the accepted transport and its UTC acquisition timestamp."""
        params = {
            "from": query.start_date.isoformat(),
            "to": query.end_date.isoformat(),
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data(
            f"https://financialmodelingprep.com/stable/{ENDPOINT}?" + urlencode(params),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query: FMPCalendarDividendQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPCalendarDividendData]]:
        """Validate every acquired row before clipping in source order."""
        if not isinstance(data.payload, list):
            raise FinancialError("invalid_response", provider="fmp")
        if not data.payload:
            raise FinancialError("missing_data", provider="fmp")
        rows = [
            validate_financial_result(FMPCalendarDividendData, row, provider="fmp")
            for row in data.payload
        ]
        retained = rows[:MAX_ROWS]
        return AnnotatedResult(
            result=retained,
            metadata=_metadata(
                query, retained, data, len(rows) > MAX_ROWS
            ).as_metadata(),
        )


def _metadata(query, rows, data, truncated):
    fields = render_field_templates(FMPCalendarDividendData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/calendar/dividend",
        provider="fmp",
        source=FinancialSource(endpoint=ENDPOINT),
        retrieved_at=data.retrieved_at,
        effective_query=query.model_dump(mode="json"),
        observation_date_field="ex_dividend_date",
        fields=fields,
        bounds=FinancialBounds(
            effective_limit=MAX_ROWS,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Currency and adjustment methodology are unknown.",
            "Yield is converted from percentage points. Annualization and price basis are unknown.",
            "Event dates are civil dates with separate roles. Timezone is unspecified.",
            "Seven days and 250 rows are local product limits. Upstream completeness is unknown.",
        ],
    )
