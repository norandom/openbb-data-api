"""Bounded FMP balance sheets with acquisition provenance and reported amounts."""

import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.balance_sheet import BalanceSheetQueryParams
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
    validate_financial_result,
)
from pydantic import Field, field_validator

from openbb_fmp.models.balance_sheet_data import FMPBalanceSheetData
from openbb_fmp.utils.definitions import validate_statement_query
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPBalanceSheetQueryParams(BalanceSheetQueryParams):
    """One security, annual or quarterly reporting dates, at most 1000 records."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["bounds", "effective_query", "retrieved_at"],
    )

    period: Literal["annual", "quarter"] = Field(default="annual")
    limit: int = Field(default=5, ge=1, le=1000)

    @field_validator("symbol", mode="before")
    @classmethod
    def single_symbol(cls, value):
        """Preserve ticker punctuation while rejecting lists and unsafe query text."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("A single symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("A single symbol is required")
        return value


class FMPBalanceSheetFetcher(
    Fetcher[FMPBalanceSheetQueryParams, list[FMPBalanceSheetData]]
):
    """Adapt the retained balance-sheet contract through the shared FMP transport."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPBalanceSheetQueryParams:
        """Reject invalid query inputs before the acquisition boundary."""
        bounded = validate_statement_query(
            params.get("symbol"),
            params.get("period", FMPBalanceSheetQueryParams.model_fields["period"].default),
            params.get("limit", FMPBalanceSheetQueryParams.model_fields["limit"].default)
        )
        return validate_financial_query(
            FMPBalanceSheetQueryParams,
            {**params, **bounded, "symbol": params.get("symbol")},
            provider="fmp",
        )

    @staticmethod
    async def aextract_data(
        query: FMPBalanceSheetQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Acquire rows and their original timestamp with typed safe transport errors."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {
            "symbol": query.symbol,
            "period": query.period,
            "limit": query.limit,
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        url = "https://financialmodelingprep.com/stable/balance-sheet-statement?"
        return await get_data_many(
            url + urlencode(params), with_provenance=True, typed_errors=True, **kwargs
        )

    @staticmethod
    def transform_data(
        query: FMPBalanceSheetQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPBalanceSheetData]]:
        """Keep latest dates first; stable ties retain provider order and duplicates."""
        rows = [
            validate_financial_result(FMPBalanceSheetData, row, provider="fmp")
            for row in data.payload
        ]
        rows.sort(key=lambda row: row.period_ending, reverse=True)
        policy = bind_query_annotation(type(query)).response_policy
        limit = getattr(query, policy.limit_parameter)
        truncated = len(rows) > limit
        rows = rows[:limit]
        metadata = _balance_metadata(query, rows, data.retrieved_at, truncated)
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _balance_fields(rows):
    """Resolve observed availability on independent class-owned stock templates."""
    fields = render_field_templates(FMPBalanceSheetData)
    for name, field in fields.items():
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    return fields


def _balance_metadata(query, rows, retrieved_at, truncated):
    """Expose bounded observations without asserting complete history or vintage safety."""
    return FinancialResultMetadata(
        dataset="equity/fundamental/balance",
        provider="fmp",
        retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="balance-sheet-statement"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": query.limit},
        fields=_balance_fields(rows),
        bounds=FinancialBounds(
            requested_limit=query.limit,
            effective_limit=query.limit,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        observation_date_field="period_ending",
        publication_date_field="filing_date",
        limitations=[
            "Provider completeness and restatement history are unavailable.",
            "Filing and acceptance dates do not establish point-in-time availability.",
            "Amounts retain provider signs and row currencies; no debt or cash bridge is calculated.",
            "Missing fields and explicit nulls remain missing; no zero or fiscal period is inferred.",
            "Latest reporting dates sort first; duplicate dates retain provider order and are not merged.",
        ],
    )
