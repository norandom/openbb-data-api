"""FMP forecasts retain fiscal-end dates without implying publication vintage."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# d64866a7cdb4719c8c61c7f10f81da919cc9e69b8f85c02af4a7e88840d7c626.
import re
from math import isfinite
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.analyst_estimates import (
    AnalystEstimatesData,
    AnalystEstimatesQueryParams,
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
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPAnalystEstimatesQueryParams(AnalystEstimatesQueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        description="One provider listing identity; maximum 50 characters.",
        max_length=50,
    )
    period: Literal["annual", "quarter"] = Field(
        default="annual",
        description="Forecast fiscal frequency; quarterly is accepted as an alias.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        strict=True,
        description="Maximum returned forecast rows; one upstream request.",
    )
    page: int = Field(
        default=0,
        ge=0,
        le=10,
        strict=True,
        description="Explicit provider page; total completeness remains unknown.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Normalize one identity while rejecting query syntax before acquisition."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("A single symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("A single symbol is required")
        return value

    @field_validator("period", mode="before")
    @classmethod
    def periodic_alias(cls, value):
        """Retain the documented quarterly spelling as a request alias."""
        return "quarter" if value == "quarterly" else value


def _forecast_template(name):
    """Fiscal end does not establish publication, duration, currency or vintage."""
    unit = None
    origin = "provider_observation"
    if name.startswith("estimated_"):
        unit = "currency/share" if "eps" in name else "currency"
        origin = "estimate"
    elif name.startswith("number_"):
        unit = "count"
    return FinancialFieldTemplate(
        unit=unit,
        scale=1 if unit else None,
        value_origin=origin,
        financial_basis={
            "forecast_period": "date is forecast fiscal period end; publication/vintage and duration unknown"
        },
        period_basis="forecast fiscal period; annual or quarter request does not establish duration or vintage",
    )


class FMPAnalystEstimatesData(AnalystEstimatesData):
    """FMP Analyst Estimates Data."""

    __alias_dict__ = {
        "estimated_revenue_low": "revenueLow",
        "estimated_revenue_high": "revenueHigh",
        "estimated_revenue_avg": "revenueAvg",
        "estimated_sga_expense_low": "sgaExpenseLow",
        "estimated_sga_expense_high": "sgaExpenseHigh",
        "estimated_sga_expense_avg": "sgaExpenseAvg",
        "estimated_ebitda_low": "ebitdaLow",
        "estimated_ebitda_high": "ebitdaHigh",
        "estimated_ebitda_avg": "ebitdaAvg",
        "estimated_ebit_low": "ebitLow",
        "estimated_ebit_high": "ebitHigh",
        "estimated_ebit_avg": "ebitAvg",
        "estimated_net_income_low": "netIncomeLow",
        "estimated_net_income_high": "netIncomeHigh",
        "estimated_net_income_avg": "netIncomeAvg",
        "estimated_eps_low": "epsLow",
        "estimated_eps_high": "epsHigh",
        "estimated_eps_avg": "epsAvg",
        "number_analyst_estimated_revenue": "numAnalystsRevenue",
        "number_analysts_estimated_eps": "numAnalystsEps",
    }
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _forecast_template(name)
                for name in AnalystEstimatesData.model_fields
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
    def safe_estimates(cls, value, handler):
        """Contain inherited amount/count conversions before exposing typed errors."""
        try:
            result = handler(value)
        except (TypeError, ValueError, OverflowError):
            pass
        else:
            if not isinstance(result, float) or isfinite(result):
                return result
        raise ValueError("Invalid financial result field")


class FMPAnalystEstimatesFetcher(
    Fetcher[FMPAnalystEstimatesQueryParams, list[FMPAnalystEstimatesData]]
):
    """Acquire one page without retries, fan-out or synthetic consensus values."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPAnalystEstimatesQueryParams:
        """Reject unsupported raw parameters before any network operation."""
        return validate_financial_query(
            FMPAnalystEstimatesQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the shared typed transport, including successful top-level emptiness."""
        from openbb_fmp.utils.helpers import get_data_many

        params = query.model_dump()
        params["apikey"] = credentials.get("fmp_api_key", "") if credentials else ""
        return await get_data_many(
            "https://financialmodelingprep.com/stable/analyst-estimates?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPAnalystEstimatesData]]:
        """Preserve source order and duplicate fiscal ends; clip only the bounded page."""
        rows = [
            validate_financial_result(FMPAnalystEstimatesData, item, provider="fmp")
            for item in data.payload
        ]
        limit = getattr(
            query, bind_query_annotation(type(query)).response_policy.limit_parameter
        )
        truncated = len(rows) > limit
        rows = rows[:limit]
        return AnnotatedResult(
            result=rows,
            metadata=_metadata(query, rows, data, limit, truncated).as_metadata(),
        )


def _metadata(query, rows, data, limit, truncated):
    """Disclose mixed source methodology and unknown response-specific lineage."""
    fields = render_field_templates(FMPAnalystEstimatesData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/estimates/historical",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="analyst-estimates",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/analyst-estimates",
        ),
        effective_query=query.model_dump(),
        fields=fields,
        bounds=FinancialBounds(
            requested_limit=limit,
            effective_limit=limit,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Date is forecast fiscal period end, not publication or as-of time; vintage and duration are unknown.",
            "Currency is unknown; amounts retain provider scale 1 and EPS is currency per share.",
            "Provider inputs may mix analyst estimates, manual adjustments and internally projected fields; response-specific lineage is unknown.",
            "Low, high, average and analyst counts remain separate source values without synthesized consensus.",
            "Page is the requested provider page; total completeness and point-in-time availability are unknown.",
        ],
    )
