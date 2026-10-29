"""Bounded FMP provider peer candidates, without analyst selection claims."""

import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_peers import (
    EquityPeersData,
    EquityPeersQueryParams,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
    ProceduralBounds,
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


class FMPEquityPeersQueryParams(EquityPeersQueryParams):
    """One source listing with bounded provider candidate output."""

    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="explicit",
        procedural_bounds=ProceduralBounds(max_symbols=1),
        response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
        runtime_properties=["retrieved_at", "source", "effective_query", "bounds"],
    )

    limit: int = Field(default=20, ge=1, le=100, strict=True, description="Maximum peer candidates, 1 to 100.")
    symbol: str = Field(max_length=50, description=EquityPeersQueryParams.model_fields["symbol"].description)

    @field_validator("symbol", mode="before")
    @classmethod
    def safe_symbol(cls, value):
        """Reject multi-symbol and URL syntax before inherited normalization."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("One nonblank symbol is required")
        maximum = next(bound.max_length for bound in cls.model_fields["symbol"].metadata if hasattr(bound, "max_length"))
        if len(value.strip()) > maximum or not re.fullmatch(r"[A-Za-z0-9^][A-Za-z0-9.^_/-]*", value.strip()):
            raise ValueError("One nonblank symbol is required")
        return value.strip().upper()


class FMPEquityPeersData(EquityPeersData, FMPDiscoveryIdentity):
    """Peer suggestions retain provider values and the source-symbol mapping."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            **FMPDiscoveryIdentity.financial_data_annotation.model_copy(deep=True).fields,
            "price": FinancialFieldTemplate(value_origin="provider_observation", unit="currency/share", currency_field="currency"),
            "market_cap": FinancialFieldTemplate(value_origin="provider_calculation", unit="currency", currency_field="currency"),
            "source_symbol": FinancialFieldTemplate(value_origin="locally_derived"),
            "candidate_basis": FinancialFieldTemplate(value_origin="locally_derived"),
        },
        runtime_properties=FMPDiscoveryIdentity.financial_data_annotation.runtime_properties.copy(),
    )

    model_config = ConfigDict(extra="ignore")

    price: float | None = Field(default=None, allow_inf_nan=False, description="Provider current price; observation date and currency may be unknown.")
    market_cap: float | None = Field(default=None, allow_inf_nan=False, validation_alias=AliasChoices("mktCap", "marketCap", "market_cap"), description="Provider market capitalization; valuation basis is unknown.")
    source_symbol: str = Field(description="Requested FMP listing from which these candidates were suggested.")
    candidate_basis: Literal["provider_suggestion"] = Field(default="provider_suggestion", description="FMP suggestion, not an analyst comparable selection.")


class FMPEquityPeersFetcher(Fetcher[FMPEquityPeersQueryParams, list[FMPEquityPeersData]]):
    """Retain provider peer order without market-cap ranking or zero suppression."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEquityPeersQueryParams:
        """Validate before any provider transport."""
        return validate_financial_query(FMPEquityPeersQueryParams, params, provider="fmp")

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the shared safe typed transport; apply the row bound locally."""
        from openbb_fmp.utils.helpers import get_data_many  # pylint: disable=import-outside-toplevel

        params = {"symbol": query.symbol, "apikey": credentials.get("fmp_api_key", "") if credentials else ""}
        return await get_data_many("https://financialmodelingprep.com/stable/stock-peers?" + urlencode(params),
                                   with_provenance=True, typed_errors=True, **kwargs)

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any) -> AnnotatedResult[list[FMPEquityPeersData]]:
        """Validate every observed row and retain clipping evidence."""
        for item in data.payload:
            if not isinstance(item, dict):
                validate_financial_result(FMPDiscoveryIdentity, item, provider="fmp")
        rows = [validate_financial_result(FMPEquityPeersData, {**item, "source_symbol": query.symbol,
                "candidate_basis": "provider_suggestion"}, provider="fmp") for item in data.payload]
        parameter = bind_query_annotation(type(query)).response_policy.limit_parameter
        rows = rows[:getattr(query, parameter)]
        return AnnotatedResult(result=rows, metadata=discovery_metadata(
            query, rows, data, FMPEquityPeersData, "stock-peers", "equity/compare/peers"))
