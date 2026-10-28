"""Financial semantics shared by provider results and generated consumer schemas."""

import re
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FINANCIAL_METADATA_KEY = "__qopenbb_financial__"
Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_./-]+$")]
QueryValue = str | int | float | bool | None | list[str | int | float | bool | None]
QUERY_PARAMETERS = frozenset({
    "symbol", "symbols", "query", "name", "exchange", "provider", "period",
    "limit", "page", "offset", "start_date", "end_date", "frequency", "units",
    "aggregation_method", "transform", "sort_order", "realtime_start", "realtime_end",
    "vintage_dates", "observation_start", "observation_end", "series_id", "series_ids",
    "use_cache", "date", "year", "quarter", "fields", "interval", "adjustment",
})


class FinancialMetadataModel(BaseModel):
    """Reject undeclared metadata and keep validation inputs out of error text."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, allow_inf_nan=False)


def _safe_public_value(value: str) -> str:
    if re.search(
        r"://|[\r\n\x00]|(?:api[\s_-]*key|(?:access|refresh|id)[\s_-]*token|"
        r"token|password|secret|authorization)\s*[=:]", value, re.I
    ):
        raise ValueError("Credential-bearing or URL values are not public query metadata")
    return value


def validate_series_id(value: str) -> str:
    """Reserve the common metadata key while retaining native FRED series IDs."""
    if not value or value == FINANCIAL_METADATA_KEY:
        raise ValueError("Series identifier is empty or reserved")
    return value


class FinancialSource(FinancialMetadataModel):
    """Identify an endpoint without publishing an authenticated request URL."""

    endpoint: Identifier | None = None
    documentation: str | None = None

    @field_validator("documentation")
    @classmethod
    def public_documentation(cls, value: str | None) -> str | None:
        """Keep request credentials and query parameters out of public references."""
        if value is None:
            return value
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or re.search(r"[\s\x00]", value)):
            raise ValueError("Documentation must be a public HTTPS reference without credentials or query")
        return value


class FinancialFieldMetadata(FinancialMetadataModel):
    """Describe meaning without inventing a common currency or financial basis."""

    definition: str = Field(min_length=1)
    unit: str | None = None
    scale: float | None = Field(default=None, gt=0)
    currency: str | None = None
    currency_field: Identifier | None = None
    period_basis: str | None = None
    value_origin: Literal[
        "provider_observation", "provider_calculation", "estimate", "locally_derived", "unknown"
    ] = "unknown"
    availability: Literal["available", "missing", "unknown"] = "unknown"
    observation_date_field: Identifier | None = None
    valuation_date_field: Identifier | None = None
    publication_date_field: Identifier | None = None
    source: Identifier | None = None
    source_unit: str | None = None
    source_frequency: str | None = None
    effective_frequency: str | None = None
    seasonal_adjustment: str | None = None
    requested_transform: str | None = None
    aggregation: str | None = None
    financial_basis: dict[Literal[
        "share_count", "debt", "cash", "lease", "minority_interest", "forecast_period", "market_date"
    ], str | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def currency_basis(self):
        """Avoid claiming one currency when rows carry their own currency basis."""
        if self.currency is not None and self.currency_field is not None:
            raise ValueError("Choose a fixed currency or a row currency field")
        return self


class FinancialBounds(FinancialMetadataModel):
    """Unknown completeness is deliberate unless a provider guarantee is recorded."""

    requested_limit: int | None = Field(default=None, ge=0, strict=True)
    effective_limit: int | None = Field(default=None, ge=0, strict=True)
    returned_count: int = Field(ge=0, strict=True)
    truncated: bool | None = None
    completeness: Literal["complete", "partial", "unknown"] = "unknown"
    completeness_basis: str | None = None
    native_continuation: str | None = None

    @field_validator("native_continuation")
    @classmethod
    def safe_continuation(cls, value: str | None) -> str | None:
        """Publish native continuation tokens without authenticated request URLs."""
        return _safe_public_value(value) if value is not None else None

    @model_validator(mode="after")
    def consistent_bounds(self):
        """Require evidence before asserting complete provider coverage."""
        if self.effective_limit is not None and self.returned_count > self.effective_limit:
            raise ValueError("Returned count exceeds effective limit")
        if self.completeness == "complete" and (self.truncated is not False or not self.completeness_basis):
            raise ValueError("Complete results require an explicit basis and no truncation")
        if self.truncated is True and self.completeness != "partial":
            raise ValueError("Observed truncation requires partial completeness")
        return self


class FinancialTransformation(FinancialMetadataModel):
    """Record an ordered transformation and the observations supporting it."""

    name: Identifier
    affected_fields: list[Identifier] = Field(min_length=1)
    source_basis: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class FinancialResultMetadata(FinancialMetadataModel):
    """Schema v1; adapters supply actual acquisition time, never serialization time."""

    schema_version: Literal[1] = 1
    dataset: Identifier
    provider: Identifier
    retrieved_at: datetime
    source: FinancialSource
    effective_query: dict[str, QueryValue] = Field(default_factory=dict)
    fields: dict[Identifier, FinancialFieldMetadata] = Field(default_factory=dict)
    bounds: FinancialBounds
    limitations: list[str] = Field(default_factory=list)
    transformations: list[FinancialTransformation] = Field(default_factory=list)
    observation_date_field: Identifier | None = None
    valuation_date_field: Identifier | None = None
    publication_date_field: Identifier | None = None
    point_in_time_safe: Literal[False] = False
    vintage_query_supported: bool | None = None
    observation_provenance: dict[str, dict[str, dict[Literal[
        "realtime_start", "realtime_end"
    ], str | None]]] = Field(default_factory=dict)

    @field_validator("retrieved_at")
    @classmethod
    def actual_utc_acquisition(cls, value: datetime) -> datetime:
        """Normalize the supplied acquisition instant without resetting freshness."""
        if value.utcoffset() is None:
            raise ValueError("Acquisition timestamp must be timezone aware")
        return value.astimezone(timezone.utc)

    @field_validator("effective_query", mode="before")
    @classmethod
    def public_query(cls, value):
        """Restrict public context to validated parameters without credential syntax."""
        if not isinstance(value, dict) or not set(value).issubset(QUERY_PARAMETERS):
            raise ValueError("Effective query contains unsupported public parameters")
        for item in value.values():
            for scalar in item if isinstance(item, list) else [item]:
                if not isinstance(scalar, (str, int, float, bool, type(None))):
                    raise ValueError("Effective query requires validated scalar parameters")
                if isinstance(scalar, str):
                    _safe_public_value(scalar)
        return value

    @field_validator("observation_provenance")
    @classmethod
    def series_namespace(cls, value):
        """Prevent series provenance from occupying the shared metadata namespace."""
        for series_id in value:
            validate_series_id(series_id)
        return value

    def as_metadata(self, existing: dict | None = None) -> dict:
        """Keep legacy series metadata intact and fail on a reserved-key collision."""
        if existing is not None and FINANCIAL_METADATA_KEY in existing:
            raise ValueError("Financial metadata namespace is already present")
        return {**(existing or {}), FINANCIAL_METADATA_KEY: self.model_dump(mode="json")}
