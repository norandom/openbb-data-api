"""FMP Income Statement Model."""

# pylint: disable=unused-argument

from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialQueryAnnotation,
    ResponsePolicy,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.standard_models.income_statement import (
    IncomeStatementQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.financial_validation import validate_financial_result
from pydantic import Field, field_validator

from openbb_fmp.models.income_statement_data import FMPIncomeStatementData
from openbb_fmp.utils.definitions import FinancialStatementPeriods
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPIncomeStatementQueryParams(IncomeStatementQueryParams):
    """FMP Income Statement Query.

    Source: https://financialmodelingprep.com/developer/docs/#Income-Statement
    """

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="baseline_default",
        response_policy=ResponsePolicy(mode="income_compatibility"),
        runtime_properties=["effective_query", "bounds", "retrieved_at"],
    )

    @field_validator("symbol", mode="after")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Trim surrounding whitespace without changing ticker punctuation."""
        return value.strip()

    @field_validator("limit", mode="after")
    @classmethod
    def bounded_limit(cls, value):
        """Preserve zero while bounding the baseline request."""
        if value is not None and value > 1000:
            raise ValueError("Limit must not exceed 1000.")
        return value

    period: FinancialStatementPeriods = Field(
        default="annual",
        description=QUERY_DESCRIPTIONS.get("period", ""),
    )


class FMPIncomeStatementFetcher(
    Fetcher[
        FMPIncomeStatementQueryParams,
        list[FMPIncomeStatementData],
    ]
):
    """FMP Income Statement Fetcher."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPIncomeStatementQueryParams:
        """Transform the query params."""
        return FMPIncomeStatementQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FMPIncomeStatementQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Return the raw data from the FMP endpoint."""
        # pylint: disable=import-outside-toplevel
        from openbb_fmp.utils.helpers import get_data_many

        api_key = credentials.get("fmp_api_key") if credentials else ""
        base_url = "https://financialmodelingprep.com/stable/income-statement"

        if query.period == "ttm":
            base_url += "-ttm"

        params = {"symbol": query.symbol, "limit": query.limit if query.limit is not None else 5,
                  "apikey": api_key}
        if query.period != "ttm":
            params["period"] = query.period
        url = f"{base_url}?{urlencode(params)}"

        return await get_data_many(url, with_provenance=True, typed_errors=False, **kwargs)

    @staticmethod
    def transform_data(
        query: FMPIncomeStatementQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPIncomeStatementData]]:
        """Return the transformed data."""
        rows = [validate_financial_result(FMPIncomeStatementData, d, provider="fmp")
                for d in data.payload]
        metadata = _income_metadata(query, rows, data.retrieved_at, len(data.payload))
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _income_metadata(query, rows, retrieved_at, observed):
    """Retain reported fiscal dates and row currencies without asserting vintage safety."""
    fields = render_field_templates(FMPIncomeStatementData)
    basis = {"annual": "annual", "quarter": "discrete_quarter", "ttm": "trailing_twelve_months"}.get(query.period)
    for name, field in fields.items():
        field.period_basis = basis
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    requested = query.limit if query.limit is not None else 5
    return FinancialResultMetadata(
        dataset="equity/fundamental/income", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="income-statement-ttm" if query.period == "ttm" else "income-statement"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": requested}, fields=fields,
        bounds=FinancialBounds(requested_limit=query.limit, returned_count=len(rows),
                               effective_limit=requested if observed <= requested else None,
                               truncated=None, completeness="unknown"),
        observation_date_field="period_ending", publication_date_field="filing_date",
        limitations=["Provider completeness and restatement history are unavailable.",
                     "Filing dates do not establish point-in-time availability.",
                     "All returned baseline rows are retained; effective limit is unknown when the provider exceeds its request."],
    )
