"""Bounded FMP cash-flow observations with acquisition and financial semantics."""

import re
from typing import Any, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.cash_flow import CashFlowStatementQueryParams
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
from pydantic import Field, field_validator

from openbb_fmp.models.cash_flow_data import FMPCashFlowStatementData
from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPCashFlowStatementQueryParams(CashFlowStatementQueryParams):
    """One symbol and one annual or discrete-quarter reporting basis."""

    period: Literal["annual", "quarter"] = Field(
        default="annual", description="Annual or discrete quarterly statements; TTM unsupported."
    )
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


class FMPCashFlowStatementFetcher(
    Fetcher[FMPCashFlowStatementQueryParams, list[FMPCashFlowStatementData]]
):
    """Retain signed reported amounts without deriving an analyst cash model."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCashFlowStatementQueryParams:
        """Validate bounds before transport without retaining unsafe input errors."""
        bounded = validate_statement_query(
            params.get("symbol"), params.get("period", "annual"), params.get("limit", 5)
        )
        return validate_financial_query(
            FMPCashFlowStatementQueryParams,
            {**params, **bounded, "symbol": params.get("symbol")}, provider="fmp",
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use typed acquisition failures and preserve the receipt timestamp."""
        from openbb_fmp.utils.helpers import get_data_many  # pylint: disable=import-outside-toplevel

        params = {"symbol": query.symbol, "period": query.period, "limit": query.limit,
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        url = "https://financialmodelingprep.com/stable/cash-flow-statement?" + urlencode(params)
        return await get_data_many(url, with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPCashFlowStatementData]]:
        """Sort newest first; retain duplicate observations in provider order."""
        rows = [validate_financial_result(FMPCashFlowStatementData, item, provider="fmp")
                for item in data.payload]
        rows.sort(key=lambda row: row.period_ending, reverse=True)
        observed = len(rows)
        rows = rows[:query.limit]
        metadata = _cash_metadata(query, rows, data.retrieved_at, observed)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _cash_fields(query, rows):
    """Currency varies by row; provider totals keep their declared cash basis unknown."""
    non_amounts = {"period_ending", "fiscal_period", "fiscal_year", "filing_date",
                   "accepted_date", "cik", "symbol", "reported_currency"}
    calculations = {"free_cash_flow", "operating_cash_flow"}
    stocks = {"cash_at_beginning_of_period", "cash_at_end_of_period"}
    periods = {row.fiscal_period for row in rows}
    basis = None
    if periods and periods <= {"FY"}:
        basis = "annual"
    elif periods and periods <= {"Q1", "Q2", "Q3", "Q4"}:
        basis = "discrete_quarter"
    fields = {}
    for name, field in FMPCashFlowStatementData.model_fields.items():
        monetary = name not in non_amounts
        fields[name] = FinancialFieldMetadata(
            definition=field.description or "Provider-reported free cash flow; calculation definition unavailable.",
            unit="currency" if monetary else None,
            scale=1 if monetary else None,
            currency_field="reported_currency" if monetary else None,
            period_basis="instant" if name in stocks else basis,
            value_origin="provider_calculation" if name in calculations else "provider_observation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
            observation_date_field=None if name == "cash_at_beginning_of_period" else "period_ending",
            publication_date_field="filing_date",
            financial_basis={"cash": None} if monetary else {},
        )
    return fields


def _cash_metadata(query, rows, retrieved_at, observed):
    """Disclose observed clipping without claiming complete historical coverage."""
    clipped = observed > query.limit
    return FinancialResultMetadata(
        dataset="equity/fundamental/cash", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="cash-flow-statement"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_cash_fields(query, rows),
        bounds=FinancialBounds(
            requested_limit=query.limit, effective_limit=query.limit, returned_count=len(rows),
            truncated=True if clipped else None, completeness="partial" if clipped else "unknown",
        ),
        observation_date_field="period_ending", publication_date_field="filing_date",
        limitations=[
            "Cash classification, restricted cash, interest/dividend classification and restatement history are unknown.",
            "Beginning cash is an instant stock whose observation date is unavailable; no period-start date is inferred.",
            "Provider operating/free cash-flow definitions are unavailable; no local cash conversion is inferred.",
            "Quarter requests preserve provider periods without deriving quarters from year-to-date amounts.",
            "Unknown or mixed fiscal-period labels leave the common period basis unknown.",
            "Filing dates do not establish point-in-time availability; historical completeness is unknown.",
            "Rows are ordered newest first; duplicates retain provider order and count toward the limit.",
        ],
    )
