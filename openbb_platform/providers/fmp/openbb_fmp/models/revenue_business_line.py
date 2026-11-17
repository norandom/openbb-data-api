"""FMP segment revenue preserves source fiscal association and exact labels."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# b30886d058e7556d7a2ce6211a677faec9e79273774a3352f1066cfa4f1c9b4b.
import re
from datetime import date
from math import isfinite
from typing import Any, ClassVar, Literal
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
from openbb_core.provider.standard_models.revenue_business_line import (
    RevenueBusinessLineData,
    RevenueBusinessLineQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPRevenueBusinessLineQueryParams(RevenueBusinessLineQueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", max_rows=1000),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        max_length=50,
        description="One provider listing identity; maximum 50 characters.",
    )
    period: Literal["annual", "quarter"] = Field(
        default="annual",
        description="Fiscal frequency; fixed structure=flat, first 1000 flattened rows, possibly splitting a fiscal period.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Validate the raw listing before native string normalization."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("One symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("One symbol is required")
        return value

    @field_validator("period", mode="before")
    @classmethod
    def fiscal_frequency(cls, value):
        """Normalize only the approved quarterly alias."""
        return "quarter" if isinstance(value, str) and value == "quarterly" else value


def _segment_template(name):
    return FinancialFieldTemplate(
        unit="currency" if name == "revenue" else None,
        scale=1 if name == "revenue" else None,
        period_basis="reported fiscal period; discrete versus year-to-date duration unknown",
        value_origin="provider_observation",
        observation_date_field="period_ending",
        publication_date_field="filing_date",
    )


class FMPRevenueBusinessLineData(RevenueBusinessLineData):
    """FMP Revenue By Business Line Data."""

    model_config = ConfigDict(allow_inf_nan=False)
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _segment_template(name)
                for name in RevenueBusinessLineData.model_fields
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("period_ending", "filing_date", mode="before")
    @classmethod
    def fiscal_date(cls, value, info):
        """Reject numeric epoch coercion and malformed reporting dates."""
        if value is None and info.field_name == "filing_date":
            return None
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        if type(value) is date:
            return value
        raise ValueError("Invalid fiscal date")

    @field_validator("revenue", mode="wrap")
    @classmethod
    def revenue_fact(cls, value, handler):
        """Preserve finite zero/fractional revenue and contain native ForceInt errors."""
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("Invalid revenue")
        try:
            number = float(value)
            if isfinite(number):
                return handler(number if isinstance(value, str) else value)
        except (TypeError, ValueError, OverflowError):
            pass
        raise ValueError("Invalid revenue")

    @field_validator("fiscal_year", mode="before")
    @classmethod
    def fiscal_year_fact(cls, value):
        """Retain nullable fiscal years without boolean or fractional coercion."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("Invalid fiscal year")
        try:
            number = float(value)
            if isfinite(number) and number.is_integer():
                return int(number)
        except (TypeError, ValueError, OverflowError):
            pass
        raise ValueError("Invalid fiscal year")


class FMPRevenueBusinessLineFetcher(
    Fetcher[FMPRevenueBusinessLineQueryParams, list[FMPRevenueBusinessLineData]]
):
    """Acquire once and flatten without aggregation or taxonomy normalization."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPRevenueBusinessLineQueryParams:
        """Reject unsupported raw parameters before acquisition."""
        return validate_financial_query(
            FMPRevenueBusinessLineQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Retain the shared typed transport's receipt, including empty success."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {**query.model_dump(), "structure": "flat"}
        params["apikey"] = credentials.get("fmp_api_key", "") if credentials else ""
        return await get_data_many(
            "https://financialmodelingprep.com/stable/revenue-product-segmentation?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPRevenueBusinessLineData]]:
        """Validate every source fact before clipping flattened source order."""
        rows = []
        for item in data.payload:
            rows.extend(_flatten(item))
        truncated = len(rows) > 1000
        rows = rows[:1000]
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata()
        )


def _flatten(item):
    if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
        raise FinancialError("invalid_response", provider="fmp")
    facts = {
        "period_ending": item.get("date"),
        "fiscal_year": item.get("fiscalYear"),
        "fiscal_period": item.get("period"),
        "filing_date": item.get("filingDate"),
    }
    # Validate period facts even if a source period has no segment labels.
    validate_financial_result(
        FMPRevenueBusinessLineData, {**facts, "revenue": 0}, provider="fmp"
    )
    return [
        validate_financial_result(
            FMPRevenueBusinessLineData,
            {**facts, "business_line": label, "revenue": revenue},
            provider="fmp",
        )
        for label, revenue in item["data"].items()
    ]


def _metadata(query, rows, data, truncated):
    fields = render_field_templates(FMPRevenueBusinessLineData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/fundamental/revenue_per_segment",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="revenue-product-segmentation",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/revenue-product-segmentation",
        ),
        effective_query=query.model_dump(),
        fields=fields,
        bounds=FinancialBounds(
            effective_limit=1000,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Currency and discrete versus year-to-date basis are unknown; no publication vintage or point-in-time safety is implied.",
            "Labels retain source order and duplicates across parsed rows; duplicate JSON keys already lost in parsing cannot be recovered.",
            "No reconciliation, aggregation or exhaustive/disjoint taxonomy claim. Clipping may split a fiscal period.",
            "Approved request caps are local conservative policies, not verified FMP maxima. One upstream call; live entitlement and consumer acceptance unverified.",
        ],
    )
