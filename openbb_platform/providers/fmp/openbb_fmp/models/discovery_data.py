"""FMP discovery identity fields and shared provenance semantics."""

import re
from urllib.parse import quote

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialResultMetadata,
    FinancialSource,
    FinancialTransformation,
)
from pydantic import AliasChoices, Field, field_validator, model_validator


class FMPDiscoveryIdentity(Data):
    """A provider listing reference is distinct from an optional issuer reference."""

    symbol: str = Field(min_length=1, description="FMP security/listing symbol, not an issuer identifier.")
    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "companyName"), description="Provider-readable company/security name.")
    exchange: str | None = Field(default=None, description="Provider exchange code or label; no exchange mapping inferred.")
    exchange_short_name: str | None = Field(default=None, validation_alias=AliasChoices("exchangeShortName", "exchange_short_name"), description="Provider short exchange code when supplied.")
    currency: str | None = Field(default=None, description="Provider-reported listing currency; unknown when omitted.")
    cik: str | None = Field(default=None, description="Provider-supplied issuer CIK; absent values remain unknown.")
    isin: str | None = Field(default=None, description="Provider-supplied security ISIN; no issuer equivalence inferred.")
    instrument_type: str | None = Field(default=None, validation_alias=AliasChoices("type", "instrument_type"), description="Provider security type when available.")
    listing_id: str | None = Field(default=None, description="Locally qualified FMP symbol and exchange reference; unknown exchange is explicit.")
    issuer_id: str | None = Field(default=None, description="FMP-qualified supplied CIK; unknown without issuer evidence.")

    @field_validator("symbol")
    @classmethod
    def nonblank_symbol(cls, value):
        """A missing listing symbol cannot identify a discovery result."""
        if not value.strip() or re.search(r"[\r\n\x00]", value):
            raise ValueError("Invalid listing symbol")
        return value

    @model_validator(mode="after")
    def qualify_identity(self):
        """Qualification preserves alternatives without treating a ticker as an issuer."""
        exchange = self.exchange_short_name or self.exchange
        suffix = "unknown" if exchange is None else "exchange:" + quote(exchange, safe="")
        self.listing_id = "fmp:symbol:" + quote(self.symbol, safe="") + ":" + suffix
        self.issuer_id = "fmp:cik:" + self.cik if self.cik else None
        return self


def discovery_metadata(query, rows, receipt, model, endpoint, dataset):
    """Retain receipt time and observed clipping without promising full coverage."""
    fields = {}
    for name, field in model.model_fields.items():
        fields[name] = FinancialFieldMetadata(
            definition=field.description or name,
            value_origin="locally_derived" if name in {"listing_id", "issuer_id", "source_symbol", "candidate_basis"} else "provider_calculation" if name == "market_cap" else "provider_observation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
            unit="currency/share" if name == "price" else "currency" if name == "market_cap" else None,
            currency_field="currency" if name in {"price", "market_cap"} else None,
        )
    clipped = len(receipt.payload) > query.limit
    effective = {"limit": query.limit}
    effective["query" if hasattr(query, "query") else "symbol"] = query.query if hasattr(query, "query") else query.symbol
    return FinancialResultMetadata(
        dataset=dataset, provider="fmp", retrieved_at=receipt.retrieved_at,
        source=FinancialSource(endpoint=endpoint), effective_query=effective, fields=fields,
        bounds=FinancialBounds(requested_limit=query.limit, effective_limit=query.limit,
                               returned_count=len(rows), truncated=True if clipped else None,
                               completeness="partial" if clipped else "unknown"),
        transformations=[FinancialTransformation(name="provider_identity_qualification", affected_fields=[name for name in ("listing_id", "issuer_id", "source_symbol", "candidate_basis") if name in model.model_fields], source_basis="Provider symbol/exchange/CIK and requested source symbol", definition="Qualify provider identities and label suggestion provenance without resolving cross-provider equivalence.")],
        limitations=[
            "Provider order and ambiguous alternatives are retained; no cross-provider identity mapping is asserted.",
            "Unknown exchange cannot establish a globally unique listing; missing issuer and security identifiers remain unknown.",
            "Provider suggestion methodology, observation dates, coverage and historical completeness are unknown.",
            "Peers are provider suggestions, not analyst-selected comparables or an investment rationale.",
        ],
    ).as_metadata()
