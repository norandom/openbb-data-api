"""FMP flow growth retains signed ratios and unknown comparison methodology."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# 10a662a63ff4781993815f083b5a074a0a5858eea64087b2d11a49afb68cf9d2.
import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_annotations import (
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
from openbb_core.provider.standard_models.income_statement_growth import (
    IncomeStatementGrowthQueryParams,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.models.income_statement_growth_data import FMPIncomeStatementGrowthData
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPIncomeStatementGrowthQueryParams(IncomeStatementGrowthQueryParams):  # noqa: D101
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
        description="Fiscal frequency; quarterly aliases quarter. Duration/denominator and restatement conventions unknown.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        strict=True,
        description="Maximum returned rows; one request; replaces archived implicit 5.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Normalize one identity while rejecting query syntax before acquisition."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
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


class FMPIncomeStatementGrowthFetcher(
    Fetcher[FMPIncomeStatementGrowthQueryParams, list[FMPIncomeStatementGrowthData]]
):
    """Acquire one bounded response without retries or inferred growth values."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPIncomeStatementGrowthQueryParams:
        """Reject unsupported raw parameters before any network operation."""
        return validate_financial_query(
            FMPIncomeStatementGrowthQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the shared typed transport, including successful top-level emptiness."""
        from openbb_fmp.utils.helpers import get_data_many

        params = query.model_dump()
        params["apikey"] = credentials.get("fmp_api_key", "") if credentials else ""
        return await get_data_many(
            "https://financialmodelingprep.com/stable/income-statement-growth?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPIncomeStatementGrowthData]]:
        """Preserve source order and duplicate fiscal ends; clip only the bounded page."""
        rows = [
            validate_financial_result(
                FMPIncomeStatementGrowthData, item, provider="fmp"
            )
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
    """Disclose source ratios and unknown comparison methodology."""
    fields = render_field_templates(FMPIncomeStatementGrowthData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/fundamental/income_growth",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="income-statement-growth",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/income-statement-growth",
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
            "Provider growth ratios retain scale 1; no local growth calculation is performed.",
            "Denominator and source comparison periods, restatement and discrete-quarter versus year-to-date methodology are unknown.",
            "Fiscal period end is not publication or vintage; point-in-time safety is not established.",
            "A quarterly query does not establish flow duration; currency is only the source reported currency when supplied.",
            "Source order and duplicate fiscal ends are retained; total completeness remains unknown unless local clipping is observed.",
        ],
    )
