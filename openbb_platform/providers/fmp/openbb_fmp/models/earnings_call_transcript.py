"""Exact-period transcripts adapted from FMP 1.6.1; see LICENSE and provenance.

Retained member SHA256: 2595d0fb54ca6134aef8295fde59222681871b4ea871fae63b0def2bcf823131.
"""

import re
from datetime import (
    date as dateType,
    datetime,
)
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
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


class FMPEarningsCallTranscriptQueryParams(QueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="FrozenEarningsCallTranscriptQuery")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="provider"),
            runtime_properties=["effective_query", "retrieved_at", "bounds"],
        )
    )
    symbol: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=1900, le=2100, strict=True)
    quarter: int = Field(ge=1, le=4, strict=True)

    @field_validator("symbol", mode="before")
    @classmethod
    def listing(cls, value):
        """Normalize a single listing without accepting coercion or query syntax."""
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9^][A-Za-z0-9.^=-]{0,49}", value
        ):
            raise ValueError("One listing required")
        return value.upper()


class FMPEarningsCallTranscriptData(Data):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="Transcript", alias_generator=None)
    symbol: str = Field(description="Company listing identity.")
    content_status: Literal[
        "partial", "metadata_only", "completeness_unknown", "full"
    ] = Field(description="Completeness of supplied text.")
    year: int = Field(ge=1900, le=2100, strict=True, description="Fiscal year.")
    quarter: str = Field(pattern=r"^Q[1-4]$", description="Fiscal quarter.")
    date: dateType = Field(description="Civil date of the call.")
    event_datetime: datetime | None = Field(
        None, description="Supplied event timestamp, preserving offset."
    )
    content: str = Field(description="Literal supplied transcript.")
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: FinancialFieldTemplate(
                    definition=None,
                    value_origin="provider_observation",
                    observation_date_field="date",
                )
                for name, definition in {
                    "symbol": "Company listing identity.",
                    "content_status": "Completeness of supplied text.",
                    "year": "Requested fiscal year.",
                    "quarter": "Requested fiscal quarter.",
                    "date": "Civil date of the call.",
                    "event_datetime": "Supplied event clock and offset; timezone unknown when absent.",
                    "content": "Literal supplied transcript, with whitespace preserved.",
                }.items()
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        """Reject absent text without changing provider whitespace or markup."""
        if not value.strip():
            raise ValueError("Nonblank content required")
        return value


class FMPEarningsCallTranscriptFetcher(
    Fetcher[FMPEarningsCallTranscriptQueryParams, list[FMPEarningsCallTranscriptData]]
):
    """Acquire precisely the requested fiscal period without discovery or fallback."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEarningsCallTranscriptQueryParams:
        """Reject invalid public input before I/O."""
        return validate_financial_query(
            FMPEarningsCallTranscriptQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Send one stable endpoint request with a safe acquisition receipt."""
        from openbb_fmp.utils.helpers import get_data

        return await get_data(
            "https://financialmodelingprep.com/stable/earning-call-transcript?"
            + urlencode(
                {
                    "symbol": query.symbol,
                    "year": query.year,
                    "quarter": query.quarter,
                    "apikey": credentials.get("fmp_api_key", "") if credentials else "",
                }
            ),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any):
        """Require one exact fiscal period and preserve literal text."""
        if not isinstance(data.payload, list) or len(data.payload) != 1:
            raise FinancialError("invalid_response", provider="fmp")
        row = _row(query, data.payload[0])
        return AnnotatedResult(
            result=[row], metadata=_metadata(query, row, data).as_metadata()
        )


def _row(query, raw):
    if (
        not isinstance(raw, dict)
        or raw.get("symbol") != query.symbol
        or type(raw.get("year")) is not int
        or raw.get("year") != query.year
        or raw.get("period") != f"Q{query.quarter}"
    ):
        raise FinancialError("invalid_response", provider="fmp")
    try:
        supplied = raw["date"]
        if not isinstance(supplied, str):
            raise ValueError("Date required")
        # Admit only civil dates or clocks representable by the public datetime.
        # ISO basic/week dates and fractional offsets must not fabricate or lose time.
        civil_only = re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", supplied)
        timestamp = re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?",
            supplied,
        )
        if not civil_only and not timestamp:
            raise ValueError("Unsupported event timestamp precision or syntax")
        event = None if civil_only else datetime.fromisoformat(supplied)
        civil = dateType.fromisoformat(supplied) if event is None else event.date()
    except (ValueError, KeyError, TypeError) as exc:
        raise FinancialError("invalid_response", provider="fmp") from exc
    return validate_financial_result(
        FMPEarningsCallTranscriptData,
        {
            "symbol": raw["symbol"],
            "year": raw["year"],
            "quarter": raw["period"],
            "date": civil,
            "event_datetime": event,
            "content": raw.get("content"),
            "content_status": "completeness_unknown",
        },
        provider="fmp",
    )


def _metadata(query, row, data):
    fields = render_field_templates(FMPEarningsCallTranscriptData)
    for name, field in fields.items():
        field.availability = (
            "available" if getattr(row, name) is not None else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/fundamental/transcript",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="earning-call-transcript",
            documentation="https://site.financialmodelingprep.com/developer/docs",
        ),
        effective_query={
            "symbol": query.symbol,
            "year": query.year,
            "quarter": query.quarter,
        },
        fields=fields,
        observation_date_field="date",
        bounds=FinancialBounds(returned_count=1, completeness="unknown"),
        limitations=[
            "Transcript completeness unknown.",
            "Timezone unknown when no offset is supplied.",
            "Exact requested fiscal period; no availability discovery or substitution.",
        ],
    )
