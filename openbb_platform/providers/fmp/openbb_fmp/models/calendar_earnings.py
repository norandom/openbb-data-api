"""Bounded earnings calendar adapted from retained FMP 1.6.1 declarations.

License: provider LICENSE and provenance.json. Retained source member SHA256:
c14722cd521d58bfca3e730ce04e622cb932f735538e86085f7c092da345f7fc.
"""

import re
from datetime import date
from typing import Any, ClassVar, Self
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.calendar_earnings import (
    CalendarEarningsData,
    CalendarEarningsQueryParams,
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

from openbb_fmp.utils.helpers import FMPAcquisition

_ENDPOINT = "earnings-calendar"
_MAX_ROWS = 250
_MAX_INCLUSIVE_DAYS = 7


def _civil_date(value: object) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Civil date required")
    return date.fromisoformat(value)


class FMPCalendarEarningsQueryParams(CalendarEarningsQueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="FrozenCalendarEarningsQuery")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            response_policy=ResponsePolicy(mode="clip", max_rows=_MAX_ROWS),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )

    start_date: date
    end_date: date

    _validate_dates = field_validator("start_date", "end_date", mode="before")(
        _civil_date
    )

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        """Require an ordered window of at most seven inclusive calendar dates."""
        if not 0 <= (self.end_date - self.start_date).days < _MAX_INCLUSIVE_DAYS:
            raise ValueError(
                "Ordered earnings calendar window must span one to seven days"
            )
        return self


def _field(
    unit: str | None = None, *, estimate: bool = False
) -> FinancialFieldTemplate:
    return FinancialFieldTemplate(
        unit=unit,
        value_origin="estimate" if estimate else "provider_observation",
        observation_date_field="report_date",
    )


class FMPCalendarEarningsData(CalendarEarningsData):  # noqa: D101
    model_config = ConfigDict(title="FrozenCalendarEarningsData", allow_inf_nan=False)
    report_date: date = Field(
        validation_alias="date",
        serialization_alias="report_date",
        description="The date of the earnings report.",
    )
    eps_previous: float | None = Field(
        default=None,
        validation_alias="eps_previous",
        description="The earnings-per-share from the same previously reported period.",
    )
    eps_consensus: float | None = Field(
        default=None,
        validation_alias="epsEstimated",
        serialization_alias="eps_consensus",
        description="The analyst conesus earnings-per-share estimate.",
    )
    eps_actual: float | None = Field(
        default=None,
        validation_alias="epsActual",
        serialization_alias="eps_actual",
        description="The actual earnings per share announced.",
    )
    revenue_consensus: float | None = Field(
        default=None,
        validation_alias="revenueEstimated",
        serialization_alias="revenue_consensus",
        description="The revenue forecast consensus.",
    )
    revenue_actual: float | None = Field(
        default=None,
        validation_alias="revenueActual",
        serialization_alias="revenue_actual",
        description="The actual reported revenue.",
    )
    last_updated: date | None = Field(
        default=None,
        validation_alias="lastUpdated",
        serialization_alias="last_updated",
        description="The date the data was updated last.",
    )
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                "report_date": _field("civil_date"),
                "symbol": _field(),
                "name": _field(),
                "eps_previous": _field("currency_per_share"),
                "eps_consensus": _field("currency_per_share", estimate=True),
                "eps_actual": _field("currency_per_share"),
                "revenue_consensus": _field("currency", estimate=True),
                "revenue_actual": _field("currency"),
                "last_updated": _field("civil_date"),
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    _validate_report_date = field_validator("report_date", mode="before")(_civil_date)

    @field_validator("last_updated", mode="before")
    @classmethod
    def optional_civil_date(cls, value: object) -> date | None:
        """Blank source updates carry no known civil date."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return _civil_date(value)

    @field_validator("symbol")
    @classmethod
    def require_symbol(cls, value: str) -> str:
        """Every market-wide row must supply its own listing identity."""
        if not value.strip():
            raise ValueError("Source listing identity required")
        return value

    @field_validator(
        "eps_previous",
        "eps_consensus",
        "eps_actual",
        "revenue_consensus",
        "revenue_actual",
        mode="before",
    )
    @classmethod
    def financial_number(cls, value: Any) -> Any:
        """Preserve numeric zeros and distinguish missing values from reported amounts."""
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("Source amount must be numeric")
        return value


class FMPCalendarEarningsFetcher(
    Fetcher[FMPCalendarEarningsQueryParams, list[FMPCalendarEarningsData]]
):
    """Acquire a market-wide earnings calendar in one bounded request."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCalendarEarningsQueryParams:
        """Admit the native query before sending any request."""
        return validate_financial_query(
            FMPCalendarEarningsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(
        query: FMPCalendarEarningsQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Use safe FMP transport and preserve its UTC retrieval receipt."""
        from openbb_fmp.utils.helpers import get_data

        wire = {
            "from": query.start_date.isoformat(),
            "to": query.end_date.isoformat(),
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data(
            f"https://financialmodelingprep.com/stable/{_ENDPOINT}?" + urlencode(wire),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query: FMPCalendarEarningsQueryParams,
        data: FMPAcquisition,
        **kwargs: Any,
    ) -> AnnotatedResult[list[FMPCalendarEarningsData]]:
        """Validate all rows before clipping in source order."""
        if not isinstance(data.payload, list) or not data.payload:
            raise FinancialError("invalid_response", provider="fmp")
        rows = [
            validate_financial_result(FMPCalendarEarningsData, row, provider="fmp")
            for row in data.payload
        ]
        truncated = len(rows) > _MAX_ROWS
        rows = rows[:_MAX_ROWS]
        metadata = _metadata(query, rows, data, truncated)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _metadata(
    query: FMPCalendarEarningsQueryParams,
    rows: list[FMPCalendarEarningsData],
    data: FMPAcquisition,
    truncated: bool,
) -> FinancialResultMetadata:
    fields = render_field_templates(FMPCalendarEarningsData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/calendar/earnings",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint=_ENDPOINT,
            documentation="https://site.financialmodelingprep.com/developer/docs",
        ),
        effective_query=query.model_dump(mode="json"),
        fields=fields,
        observation_date_field="report_date",
        bounds=FinancialBounds(
            requested_limit=_MAX_ROWS,
            effective_limit=_MAX_ROWS,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Currency and adjustment methodology are unknown.",
            "Event confirmation status, fiscal period and time zone are unknown.",
            "Product caps do not establish provider maxima, account entitlement or exhaustive coverage.",
        ],
    )
