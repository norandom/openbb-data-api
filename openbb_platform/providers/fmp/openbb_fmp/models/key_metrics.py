"""Periodic FMP metrics with explicit units and unknown valuation conventions."""

import re
from datetime import date
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
from openbb_core.provider.standard_models.key_metrics import KeyMetricsQueryParams
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import Field, field_validator

from openbb_fmp.models.key_metrics_data import FMPKeyMetricsData
from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPKeyMetricsQueryParams(KeyMetricsQueryParams):
    """Single-symbol periodic observations; TTM synthesis is unsupported."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["bounds", "effective_query", "retrieved_at"],
    )

    period: Literal["annual", "quarter"] = Field(default="annual")
    limit: int = Field(default=5, ge=1, le=1000)
    ttm: Literal["exclude"] = Field(default="exclude", description="Only periodic data is supported.")

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Reject unsafe query text before encoding the provider URL."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("A single symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("A single symbol is required")
        return value


class FMPKeyMetricsFetcher(Fetcher[FMPKeyMetricsQueryParams, list[FMPKeyMetricsData]]):
    """Fetch periodic metrics without fetching or fabricating TTM observations."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPKeyMetricsQueryParams:
        """Validate before any provider I/O."""
        bounded = validate_statement_query(
            params.get("symbol"),
            params.get("period", FMPKeyMetricsQueryParams.model_fields["period"].default),
            params.get("limit", FMPKeyMetricsQueryParams.model_fields["limit"].default),
        )
        return validate_financial_query(
            FMPKeyMetricsQueryParams, {**params, **bounded, "symbol": params.get("symbol")},
            provider="fmp",
        )

    @staticmethod
    async def aextract_data(
        query: FMPKeyMetricsQueryParams, credentials: dict[str, str] | None, **kwargs: Any,
    ) -> FMPAcquisition:
        """Retain the transport's actual acquisition receipt."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {"symbol": query.symbol, "period": query.period, "limit": query.limit,
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        return await get_data_many(
            "https://financialmodelingprep.com/stable/key-metrics?" + urlencode(params),
            with_provenance=True, typed_errors=True, **kwargs,
        )

    @staticmethod
    def transform_data(
        query: FMPKeyMetricsQueryParams, data: FMPAcquisition, **kwargs: Any,
    ) -> AnnotatedResult[list[FMPKeyMetricsData]]:
        """Latest known dates first, stable duplicates, undated rows last."""
        rows = [validate_financial_result(FMPKeyMetricsData, row, provider="fmp")
                for row in data.payload]
        rows.sort(key=lambda row: row.period_ending or date.min, reverse=True)
        policy = bind_query_annotation(type(query)).response_policy
        limit = getattr(query, policy.limit_parameter)
        truncated = len(rows) > limit
        rows = rows[:limit]
        return AnnotatedResult(result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata())


def _fields(rows):
    """Fiscal labels do not establish the method window or market valuation date."""
    fields = render_field_templates(FMPKeyMetricsData)
    periods = {row.fiscal_period for row in rows}
    period_basis = "annual" if periods == {"FY"} else None
    if periods and periods.issubset({"Q1", "Q2", "Q3", "Q4"}):
        period_basis = "discrete_quarter"
    for name, field in fields.items():
        if field.value_origin == "provider_calculation":
            field.period_basis = period_basis
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    return fields


def _metadata(query, rows, data, truncated):
    """Disclose bounded source observations without completeness or valuation claims."""
    return FinancialResultMetadata(
        dataset="equity/fundamental/metrics", provider="fmp", retrieved_at=data.retrieved_at,
        source=FinancialSource(endpoint="key-metrics",
                               documentation="https://site.financialmodelingprep.com/developer/docs/stable/key-metrics"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_fields(rows),
        bounds=FinancialBounds(requested_limit=query.limit, effective_limit=query.limit,
                               returned_count=len(rows), truncated=True if truncated else None,
                               completeness="partial" if truncated else "unknown"),
        observation_date_field="period_ending",
        limitations=[
            "Values are provider calculations, not a local valuation model; no TTM rows are synthesized.",
            "Only modeled fields are exposed; unmodeled provider fields are omitted to avoid undocumented units.",
            "Fiscal period labels are retained; individual calculation windows and annualization conventions are unknown.",
            "Fraction values are unscaled; display percentages require multiplication by 100.",
            "Market-input dates, share-count, lease, debt/cash and minority-interest conventions are unknown.",
            "Row currency is retained when supplied; missing dates, currency and fiscal labels are not inferred.",
            "Completeness, revisions and point-in-time availability are unknown; duplicate dates are retained.",
        ],
    )
