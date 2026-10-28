"""Bounded periodic FMP ratio observations with acquisition and financial semantics."""

import re
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
from openbb_core.provider.standard_models.financial_ratios import (
    FinancialRatiosQueryParams,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import Field, field_validator

from openbb_fmp.models.financial_ratios_data import FMPFinancialRatiosData
from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPFinancialRatiosQueryParams(FinancialRatiosQueryParams):
    """One symbol and one annual or discrete-quarter reporting basis."""

    period: Literal["annual", "quarter"] = Field(
        default="annual", description="Annual or discrete quarterly statements; TTM unsupported."
    )
    ttm: Literal["exclude"] = Field(default="exclude", description="Only periodic ratios are supported.")
    limit: int = Field(default=5, ge=1, le=1000, description="Maximum statement rows, 1 to 1000.")

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
        bounded = validate_statement_query(
            params.get("symbol"), params.get("period", "annual"), params.get("limit", 5)
        )
        return validate_financial_query(
            FMPFinancialRatiosQueryParams,
            {**params, **bounded, "symbol": params.get("symbol")}, provider="fmp",
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
        rows = rows[:query.limit]
        metadata = _ratio_metadata(query, rows, data.retrieved_at, observed)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _ratio_fields(rows):
    """Classify each quantity without rescaling provider observations."""
    identity = {"symbol", "period_ending", "fiscal_year", "fiscal_period", "currency"}
    fractions = {"solvency_ratio", "debt_to_assets", "debt_to_capital", "long_term_debt_to_capital",
                 "debt_to_market_cap", "net_income_per_ebt", "ebt_per_ebit",
                 "effective_tax_rate", "dividend_yield", "dividend_payout_ratio",
                 "operating_cash_flow_sales_ratio", "free_cash_flow_operating_cash_flow_ratio"}
    multiples = {
        'receivables_turnover',
        'payables_turnover',
        'inventory_turnover',
        'fixed_asset_turnover',
        'asset_turnover',
        'current_ratio',
        'quick_ratio',
        'cash_ratio',
        'price_to_earnings',
        'price_to_earnings_growth',
        'forward_price_to_earnings_growth',
        'price_to_book',
        'price_to_sales',
        'price_to_free_cash_flow',
        'price_to_operating_cash_flow',
        'debt_to_equity',
        'financial_leverage_ratio',
        'working_capital_turnover_ratio',
        'operating_cash_flow_ratio',
        'debt_service_coverage_ratio',
        'interest_coverage_ratio',
        'short_term_operating_cash_flow_coverage_ratio',
        'operating_cash_flow_coverage_ratio',
        'capital_expenditure_coverage_ratio',
        'dividend_paid_and_capex_coverage_ratio',
        'price_to_fair_value',
        'enterprise_value_multiple',
        'price_to_earnings_diluted',
        'price_to_earnings_diluted_growth',
    }
    periods = {row.fiscal_period for row in rows}
    basis = "annual" if periods and periods <= {"FY"} else None
    if periods and periods <= {"Q1", "Q2", "Q3", "Q4"}:
        basis = "discrete_quarter"
    fields = {}
    for name, field in FMPFinancialRatiosData.model_fields.items():
        unit = "multiple" if name in multiples else None
        if name in fractions or name.endswith("_margin"):
            unit = "fraction"
        if name.endswith("_per_share"):
            unit = "currency/share"
        if name == "dividend_yield_percentage":
            unit = "percent"
        fields[name] = FinancialFieldMetadata(
            definition=(field.description or name) + (
                " Provider calculation; exact accounting and averaging conventions unavailable."
                if name not in identity else ""),
            unit=unit, scale=1 if unit else None,
            currency_field="currency" if unit == "currency/share" else None,
            period_basis=None if name in identity else basis,
            observation_date_field="period_ending" if name in identity else None,
            financial_basis={"share_count": None, "debt": None, "cash": None,
                             "lease": None, "minority_interest": None,
                             "forecast_period": None, "market_date": None} if unit else {},
            value_origin="provider_observation" if name in identity else "provider_calculation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
        )
    return fields


def _ratio_metadata(query, rows, retrieved_at, observed):
    """Disclose clipped observations and unknown historical completeness."""
    clipped = observed > query.limit
    return FinancialResultMetadata(
        dataset="equity/fundamental/ratios", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="ratios", documentation="https://site.financialmodelingprep.com/developer/docs/stable/metrics-ratios"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_ratio_fields(rows),
        bounds=FinancialBounds(requested_limit=query.limit, effective_limit=query.limit,
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
