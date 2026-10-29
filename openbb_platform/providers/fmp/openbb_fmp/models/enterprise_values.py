"""Bounded FMP enterprise-value inputs with explicit unknown valuation conventions."""

import re
from datetime import date
from typing import Any
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.enterprise_values import (
    EnterpriseValuesData,
    EnterpriseValuesQueryParams,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import AliasChoices, Field, field_validator

from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPEnterpriseValuesQueryParams(EnterpriseValuesQueryParams):
    """Reject unsafe symbols before provider I/O."""

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Accept one bounded listing identity without URL query syntax."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("A single symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("A single symbol is required")
        return value


class FMPEnterpriseValuesData(EnterpriseValuesData):
    """Map stable FMP components without reversing cash signs or recomputing EV."""

    currency: str | None = Field(default=None, validation_alias=AliasChoices("reportedCurrency", "currency"), description="Explicit provider row currency, otherwise unknown.")
    market_cap: float | None = Field(default=None, validation_alias=AliasChoices("marketCapitalization", "marketCap", "market_cap"), description="Provider market capitalization in row currency; valuation basis unknown.")
    cash_and_cash_equivalents: float | None = Field(default=None, validation_alias=AliasChoices("minusCashAndCashEquivalents", "cashAndCashEquivalents", "cash_and_cash_equivalents"), description="Provider cash component as supplied in row currency; the minus prefix does not change its sign.")
    total_debt: float | None = Field(default=None, validation_alias=AliasChoices("addTotalDebt", "totalDebt", "total_debt"), description="Provider debt component as supplied in row currency; lease conventions unknown.")


class FMPEnterpriseValuesFetcher(Fetcher[FMPEnterpriseValuesQueryParams, list[FMPEnterpriseValuesData]]):
    """Use the native Fetcher lifecycle and the shared safe acquisition transport."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEnterpriseValuesQueryParams:
        """Enforce single-symbol periodic bounds before extraction."""
        bounded = validate_statement_query(params.get("symbol"), params.get("period", "annual"), params.get("limit", 5))
        return validate_financial_query(FMPEnterpriseValuesQueryParams,
            {**params, **bounded, "symbol": params.get("symbol")}, provider="fmp")

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Send the documented stable endpoint parameters and retain retrieval time."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {"symbol": query.symbol, "period": query.period, "limit": query.limit,
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        return await get_data_many("https://financialmodelingprep.com/stable/enterprise-values?" + urlencode(params),
                                   with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPEnterpriseValuesData]]:
        """Latest dated rows first; preserve duplicate source order and put undated rows last."""
        rows = [validate_financial_result(FMPEnterpriseValuesData, item, provider="fmp") for item in data.payload]
        rows.sort(key=lambda row: row.date or date.min, reverse=True)
        truncated = len(rows) > query.limit
        rows = rows[:query.limit]
        return AnnotatedResult(result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata())


def _fields(rows):
    """A fiscal observation date never establishes the underlying market-input date."""
    fields = {}
    for name, field in FMPEnterpriseValuesData.model_fields.items():
        monetary = name in {"stock_price", "market_cap", "cash_and_cash_equivalents", "total_debt", "enterprise_value"}
        unit = "currency/share" if name == "stock_price" else "currency" if monetary else None
        if name == "number_of_shares":
            unit = "shares"
        fields[name] = FinancialFieldMetadata(
            definition=field.description or name, unit=unit, scale=1 if unit else None,
            currency_field="currency" if monetary else None,
            value_origin="provider_calculation" if name in {"market_cap", "enterprise_value"} else "provider_observation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
            observation_date_field="date",
            financial_basis={"share_count": None, "debt": None, "cash": None, "lease": None,
                             "minority_interest": None, "forecast_period": None, "market_date": None},
        )
    return fields


def _metadata(query, rows, data, truncated):
    """Expose inputs, not a reconciled or analyst-adjusted enterprise-value bridge."""
    return FinancialResultMetadata(
        dataset="equity/fundamental/enterprise_values", provider="fmp", retrieved_at=data.retrieved_at,
        source=FinancialSource(endpoint="enterprise-values",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/enterprise-values"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_fields(rows), observation_date_field="date",
        bounds=FinancialBounds(requested_limit=query.limit, effective_limit=query.limit,
            returned_count=len(rows), truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown"),
        limitations=[
            "Provider values are retained without a local enterprise-value calculation or analyst adjustments.",
            "Source dates do not establish price/share as-of dates or alignment with cash and debt dates.",
            "Share-count, lease, debt/cash, minority-interest and forecast conventions are unknown.",
            "Currency is retained only when explicitly supplied; source reporting currency is not inferred.",
            "Completeness and point-in-time availability are unknown; duplicate dates retain source order.",
        ],
    )
