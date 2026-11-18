"""FMP market-wide split events with explicit new and old share components."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# 3354ebf3b4669bdde75c7e3996b3c1c8776b564866bdc695bd0eda2eb84c8138.
import re
from datetime import date
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.calendar_splits import (
    CalendarSplitsData,
    CalendarSplitsQueryParams,
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
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition, get_data

ENDPOINT = "splits-calendar"
MAX_ROWS = 250


def _civil_date(value: Any) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("A civil date in YYYY-MM-DD format is required")


class FMPCalendarSplitsQueryParams(CalendarSplitsQueryParams):
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


class FMPCalendarSplitsData(CalendarSplitsData):
    """Keep new shares over old shares, including reverse split observations."""

    __alias_dict__ = {}
    model_config = ConfigDict(allow_inf_nan=False)
    numerator: float = Field(gt=0, description="New shares")
    denominator: float = Field(gt=0, description="Old shares")
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: FinancialFieldTemplate(
                    source=name,
                    unit="civil_date"
                    if name == "date"
                    else ("shares" if name in ("numerator", "denominator") else None),
                    value_origin="provider_observation",
                )
                for name in CalendarSplitsData.model_fields
            },
            runtime_properties=["fields.availability"],
        )
    )
    _event_date = field_validator("date", mode="before")(_civil_date)

    @field_validator("symbol")
    @classmethod
    def source_symbol(cls, value):
        """Require attribution for each market-wide event."""
        if not value.strip():
            raise ValueError("A listing identity is required")
        return value

    @field_validator("numerator", "denominator", mode="before")
    @classmethod
    def numeric_component(cls, value):
        """Never infer missing share components or coerce strings and booleans."""
        if type(value) not in (int, float):
            raise ValueError("A positive finite numeric component is required")
        return value


class FMPCalendarSplitsFetcher(
    Fetcher[FMPCalendarSplitsQueryParams, list[FMPCalendarSplitsData]]
):
    """Acquire the admitted window once and cap the fully validated results."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCalendarSplitsQueryParams:
        """Apply typed validation before preparing the upstream request."""
        return validate_financial_query(
            FMPCalendarSplitsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(
        query: FMPCalendarSplitsQueryParams,
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
        query: FMPCalendarSplitsQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPCalendarSplitsData]]:
        """Validate every acquired row before clipping in source order."""
        if not isinstance(data.payload, list):
            raise FinancialError("invalid_response", provider="fmp")
        if not data.payload:
            raise FinancialError("missing_data", provider="fmp")
        rows = [
            validate_financial_result(FMPCalendarSplitsData, row, provider="fmp")
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
    fields = render_field_templates(FMPCalendarSplitsData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/calendar/splits",
        provider="fmp",
        source=FinancialSource(endpoint=ENDPOINT),
        retrieved_at=data.retrieved_at,
        effective_query=query.model_dump(mode="json"),
        observation_date_field="date",
        fields=fields,
        bounds=FinancialBounds(
            effective_limit=MAX_ROWS,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Numerator is new shares; denominator is old shares. No price adjustment is performed.",
            "Event dates are civil dates. Timezone is unspecified.",
            "Seven days and 250 rows are local product limits. Upstream completeness is unknown.",
        ],
    )
