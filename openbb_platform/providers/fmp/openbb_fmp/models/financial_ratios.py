"""Bounded periodic FMP ratio observations with acquisition and financial semantics."""

import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialQueryAnnotation,
    ResponsePolicy,
    bind_query_annotation,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.standard_models.financial_ratios import (
    FinancialRatiosQueryParams,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import Field, field_validator

from openbb_fmp.models.financial_ratios_data import FMPFinancialRatiosData
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPFinancialRatiosQueryParams(FinancialRatiosQueryParams):
    """One symbol and one annual or discrete-quarter reporting basis."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["bounds", "effective_query", "retrieved_at"],
    )

    period: Literal["annual", "quarter"] = Field(
        default="annual", description="Annual or discrete quarterly statements; TTM unsupported."
    )
    ttm: Literal["exclude"] = Field(default="exclude", description="Only periodic ratios are supported.")
    limit: int = Field(default=5, ge=1, le=1000, strict=True, description="Maximum statement rows, 1 to 1000.")

    @field_validator("period", mode="before")
    @classmethod
    def periodic_alias(cls, value):
        """Retain the accepted quarterly spelling without copying period choices."""
        return "quarter" if value == "quarterly" else value

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Reject lists and URL syntax before the inherited uppercase conversion."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("One nonblank symbol is required.")
        if not re.fullmatch(r"[A-Za-z0-9^][A-Za-z0-9.^_/-]{0,49}", value.strip()):
            raise ValueError("One nonblank symbol is required.")
        return value.strip().upper()


class FMPFinancialRatiosFetcher(
    Fetcher[FMPFinancialRatiosQueryParams, list[FMPFinancialRatiosData]]
):
    """Retain provider ratios without deriving analyst metrics."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPFinancialRatiosQueryParams:
        """Validate bounds before transport without retaining unsafe input errors."""
        return validate_financial_query(
            FMPFinancialRatiosQueryParams,
            params, provider="fmp",
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use typed acquisition failures and preserve the receipt timestamp."""
        from openbb_fmp.utils.helpers import get_data_many  # pylint: disable=import-outside-toplevel

        params = {"symbol": query.symbol, "period": query.period, "limit": query.limit,
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        url = "https://financialmodelingprep.com/stable/ratios?" + urlencode(params)
        return await get_data_many(url, with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPFinancialRatiosData]]:
        """Sort newest first; retain duplicate observations in provider order."""
        rows = [validate_financial_result(FMPFinancialRatiosData, item, provider="fmp")
                for item in data.payload]
        rows.sort(key=lambda row: row.period_ending, reverse=True)
        observed = len(rows)
        policy = bind_query_annotation(type(query)).response_policy
        limit = getattr(query, policy.limit_parameter)
        rows = rows[:limit]
        metadata = _ratio_metadata(query, rows, data.retrieved_at, observed)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _ratio_fields(rows):
    """Resolve observed fiscal labels and availability on independent templates."""
    fields = render_field_templates(FMPFinancialRatiosData)
    periods = {row.fiscal_period for row in rows}
    basis = "annual" if periods and periods <= {"FY"} else None
    if periods and periods <= {"Q1", "Q2", "Q3", "Q4"}:
        basis = "discrete_quarter"
    for name, field in fields.items():
        if field.value_origin == "provider_calculation":
            field.period_basis = basis
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    return fields


def _ratio_metadata(query, rows, retrieved_at, observed):
    """Disclose clipped observations and unknown historical completeness."""
    policy = bind_query_annotation(type(query)).response_policy
    limit = getattr(query, policy.limit_parameter)
    clipped = observed > limit
    return FinancialResultMetadata(
        dataset="equity/fundamental/ratios", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="ratios", documentation="https://site.financialmodelingprep.com/developer/docs/stable/metrics-ratios"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_ratio_fields(rows),
        bounds=FinancialBounds(requested_limit=limit, effective_limit=limit,
                               returned_count=len(rows), truncated=True if clipped else None,
                               completeness="partial" if clipped else "unknown"),
        observation_date_field="period_ending",
        limitations=[
            "Provider calculations are not locally computed analyst metrics; accounting, averaging and PEG growth conventions are unavailable.",
            "Per-share currency references each row; missing currency is not inferred.",
            "No market valuation date, publication date, restatement history or point-in-time safety is established.",
            "Annual/discrete-quarter basis follows actual fiscal labels; mixed or unknown labels retain unknown basis.",
            "Fiscal labels do not establish calculation windows, annualization or individual market observation dates.",
            "Rows are newest first; duplicates retain provider order and count toward the limit.",
            "Dividend yield is a fraction; dividend yield percentage is percentage points. Neither is rescaled.",
        ],
    )
