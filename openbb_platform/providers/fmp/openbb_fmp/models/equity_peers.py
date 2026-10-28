"""Bounded FMP provider peer candidates, without analyst selection claims."""

import re
from typing import Any, Literal
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_peers import (
    EquityPeersData,
    EquityPeersQueryParams,
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

    limit: int = Field(default=20, ge=1, le=100, strict=True, description="Maximum peer candidates, 1 to 100.")

    @field_validator("symbol", mode="before")
    @classmethod
    def safe_symbol(cls, value):
        """Reject multi-symbol and URL syntax before inherited normalization."""
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value):
            raise ValueError("One nonblank symbol is required")
        if not re.fullmatch(r"[A-Za-z0-9^][A-Za-z0-9.^_/-]{0,49}", value.strip()):
            raise ValueError("One nonblank symbol is required")
        return value.strip().upper()


class FMPEquityPeersData(EquityPeersData, FMPDiscoveryIdentity):
    """Peer suggestions retain provider values and the source-symbol mapping."""

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
        rows = rows[:query.limit]
        return AnnotatedResult(result=rows, metadata=discovery_metadata(
            query, rows, data, FMPEquityPeersData, "stock-peers", "equity/compare/peers"))
