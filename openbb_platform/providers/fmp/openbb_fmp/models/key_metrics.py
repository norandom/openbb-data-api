"""Periodic FMP metrics with explicit units and unknown valuation conventions."""

import re
from datetime import date
from typing import Any, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
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
            params.get("symbol"), params.get("period", "annual"), params.get("limit", 5)
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
        truncated = len(rows) > query.limit
        rows = rows[:query.limit]
        return AnnotatedResult(result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata())


IDENTITY = {"symbol", "period_ending", "fiscal_year", "fiscal_period", "currency"}
CURRENCY = {
    "market_cap", "enterprise_value", "working_capital", "invested_capital",
    "average_receivables", "average_payables", "average_inventory",
    "free_cash_flow_to_equity", "free_cash_flow_to_firm", "tangible_asset_value",
    "net_current_asset_value",
}
PER_SHARE = {"graham_number", "graham_net_net"}
DAYS = {
    "days_of_sales_outstanding", "days_of_payables_outstanding", "days_of_inventory_outstanding",
    "operating_cycle", "cash_conversion_cycle",
}
MULTIPLES = {
    "ev_to_sales", "ev_to_operating_cash_flow", "ev_to_free_cash_flow", "ev_to_ebitda",
    "net_debt_to_ebitda", "current_ratio", "income_quality", "capex_to_depreciation",
}
FRACTIONS = {
    "tax_burden", "interest_burden", "return_on_assets", "operating_return_on_assets",
    "return_on_tangible_assets", "return_on_equity", "return_on_invested_capital",
    "return_on_capital_employed", "earnings_yield", "free_cash_flow_yield",
    "capex_to_operating_cash_flow", "capex_to_revenue",
    "sales_general_and_administrative_to_revenue", "research_and_development_to_revenue",
    "stock_based_compensation_to_revenue", "intangibles_to_total_assets",
}


def _unit(name):
    """Use declared financial categories rather than guessing units from field names."""
    for names, unit in [(CURRENCY, "currency"), (PER_SHARE, "currency/share"),
                        (DAYS, "days"), (MULTIPLES, "multiple"), (FRACTIONS, "fraction")]:
        if name in names:
            return unit
    return None


def _fields(rows):
    """Fiscal labels do not establish the method window or market valuation date."""
    fields = {}
    periods = {row.fiscal_period for row in rows}
    period_basis = "annual" if periods == {"FY"} else None
    if periods and periods.issubset({"Q1", "Q2", "Q3", "Q4"}):
        period_basis = "discrete_quarter"
    for name, field in FMPKeyMetricsData.model_fields.items():
        unit = _unit(name)
        fields[name] = FinancialFieldMetadata(
            definition=field.description or name, unit=unit,
            scale=1 if unit else None, currency_field="currency" if name in CURRENCY | PER_SHARE else None,
            period_basis=period_basis if name not in IDENTITY else None,
            value_origin="provider_observation" if name in IDENTITY else "provider_calculation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
            observation_date_field="period_ending" if name in IDENTITY else None,
            financial_basis={} if name in IDENTITY else {
                "share_count": None, "debt": None, "cash": None, "lease": None,
                "minority_interest": None, "forecast_period": None, "market_date": None,
            },
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
