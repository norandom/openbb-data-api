"""Bounded FMP name and symbol discovery, retaining alternative listings."""

import re
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_search import (
    EquitySearchData,
    EquitySearchQueryParams,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialQueryAnnotation,
    ResponsePolicy,
    bind_query_annotation,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import AliasChoices, ConfigDict, Field, field_validator

from openbb_fmp.models.discovery_data import FMPDiscoveryIdentity, discovery_metadata
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPEquitySearchQueryParams(EquitySearchQueryParams):
    """One nonblank name or symbol search; this is not a financial screener."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["retrieved_at", "source", "effective_query", "bounds"],
    )

    limit: int = Field(default=20, ge=1, le=100, strict=True, description="Maximum discovery alternatives, 1 to 100.")
    query: str = Field(default="", max_length=200, description="Search query.")

    @field_validator("query", mode="before")
    @classmethod
    def safe_query(cls, value):
        """Reject unsafe public query metadata before provider I/O."""
        maximum = next(bound.max_length for bound in cls.model_fields["query"].metadata if hasattr(bound, "max_length"))
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError("A bounded nonblank search is required")
        if re.search(r"://|[\r\n\x00]|(?:api[ _-]*key|token|password|secret|authorization)\s*[=:]", value, re.IGNORECASE):
            raise ValueError("Unsafe search query")
        return value.strip()


class FMPEquitySearchData(EquitySearchData, FMPDiscoveryIdentity):
    """Provider discovery attributes without inferred issuer consolidation."""

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field(min_length=1, description="FMP listing symbol, not an issuer identifier.")
    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "companyName"), description="Provider company/security name.")


class FMPEquitySearchFetcher(Fetcher[FMPEquitySearchQueryParams, list[FMPEquitySearchData]]):
    """Search the chosen provider endpoint without deduplicating ambiguous listings."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEquitySearchQueryParams:
        """Validate search bounds before extraction."""
        return validate_financial_query(FMPEquitySearchQueryParams, params, provider="fmp")

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Capture the actual shared transport acquisition timestamp."""
        from openbb_fmp.utils.helpers import get_data_many  # pylint: disable=import-outside-toplevel

        endpoint = "search-symbol" if query.is_symbol else "search-name"
        params = {"query": query.query, "limit": query.limit,
                  "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        return await get_data_many("https://financialmodelingprep.com/stable/" + endpoint + "?" + urlencode(params),
                                   with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPEquitySearchData]]:
        """Preserve provider order, duplicates and unknown identifiers."""
        rows = [validate_financial_result(FMPEquitySearchData, item, provider="fmp") for item in data.payload]
        parameter = bind_query_annotation(type(query)).response_policy.limit_parameter
        rows = rows[:getattr(query, parameter)]
        endpoint = "search-symbol" if query.is_symbol else "search-name"
        return AnnotatedResult(result=rows, metadata=discovery_metadata(
            query, rows, data, FMPEquitySearchData, endpoint, "equity/search"))
