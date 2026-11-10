"""Bounded FMP cash-flow observations with acquisition and financial semantics."""

import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.cash_flow import CashFlowStatementQueryParams
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
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
)
from pydantic import Field, field_validator

from openbb_fmp.models.cash_flow_data import FMPCashFlowStatementData
from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition
from openbb_fmp.utils.statement_provenance import statement_bundles, with_statement_provenance


class FMPCashFlowStatementQueryParams(CashFlowStatementQueryParams):
    """One symbol and one requested annual or quarterly frequency."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["bounds", "effective_query", "retrieved_at"],
    )

    period: Literal["annual", "quarter"] = Field(
        default="annual", description="Requested annual or quarterly statements; actual flow coverage is unverified. TTM unsupported."
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
        # Native standard queries serialize an omitted optional limit as None.
        limit = params.get("limit")
        if limit is None:
            limit = FMPCashFlowStatementQueryParams.model_fields["limit"].default
        bounded = validate_statement_query(
            params.get("symbol"),
            params.get("period", FMPCashFlowStatementQueryParams.model_fields["period"].default),
            limit,
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
        bundles = statement_bundles(FMPCashFlowStatementData, data.payload)
        bundles.sort(key=lambda bundle: bundle.row.period_ending, reverse=True)
        observed = len(bundles)
        policy = bind_query_annotation(type(query)).response_policy
        bundles = bundles[:getattr(query, policy.limit_parameter)]
        rows = [bundle.row for bundle in bundles]
        metadata = _cash_metadata(query, rows, data.retrieved_at, observed)
        metadata = with_statement_provenance(metadata, query, bundles)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _cash_fields(query, rows):
    """Currency varies by row; provider totals keep their declared cash basis unknown."""
    fields = render_field_templates(FMPCashFlowStatementData)
    for name, field in fields.items():
        if field.period_basis != "instant":
            field.period_basis = None
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
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
            "Fiscal-period labels do not verify flow duration; the common flow basis remains unknown.",
            "Filing dates do not establish point-in-time availability; historical completeness is unknown.",
            "Rows are ordered newest first; duplicates retain provider order and count toward the limit.",
        ],
    )
