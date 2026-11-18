"""Bounded stock news adapted from retained FMP 1.6.1 declarations.

License: provider LICENSE and provenance.json. Retained source member SHA256:
9359dd750effb8a2f104922c4c9b592c3c5efaf788616170ea0a93df1bef34e1.
"""

import re
from datetime import date, datetime
from typing import Any, ClassVar, Literal, Self
from urllib.parse import urlencode, urlsplit

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
    ResponsePolicy,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition

_ORIGINS = {
    "symbol": "symbol",
    "date": "publishedDate",
    "title": "title",
    "source": "site",
    "publisher": "publisher",
    "excerpt": "text",
    "url": "url",
    "symbols": "symbol",
    "images": "image",
}


class FMPCompanyNewsQueryParams(QueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="FrozenCompanyNewsQuery")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    page: int = Field(0, strict=True, ge=0, le=99)
    limit: int = Field(10, strict=True, ge=1, le=50)

    @model_validator(mode="before")
    @classmethod
    def explicit_values(cls, value: Any) -> Any:
        """Omission is distinct from an explicitly unknown query choice."""
        if isinstance(value, dict) and any(x is None for x in value.values()):
            raise ValueError("Explicit null is not omission")
        return value

    @field_validator("symbol")
    @classmethod
    def listing(cls, value: str) -> str:
        """Require a single listing without silently removing whitespace."""
        if "," in value or any(c.isspace() for c in value):
            raise ValueError("Exactly one listing required")
        return value.upper()

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def civil_bound(cls, value: Any) -> date:
        """Dates are civil boundaries, never epoch or timestamp coercions."""
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
        ):
            raise ValueError("Civil date required")
        return date.fromisoformat(value)

    @model_validator(mode="after")
    def paired_window(self) -> Self:
        """Bound the optional paired window to 31 inclusive dates."""
        if bool(self.start_date) != bool(self.end_date):
            raise ValueError("Dates must be paired")
        if self.start_date and not 0 <= (self.end_date - self.start_date).days < 31:
            raise ValueError("Invalid inclusive window")
        return self


class FMPCompanyNewsData(Data):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="News", alias_generator=None)
    symbol: str = Field(
        description="Normalized listing symbol linking the article to the requested company."
    )
    content_status: Literal[
        "partial", "metadata_only", "completeness_unknown", "full"
    ] = Field(
        description="Locally derived coverage status; supplied excerpts are partial and headlines alone are metadata-only."
    )
    date: datetime = Field(
        description="Source publication timestamp preserving supplied precision and offset; an unsupplied timezone remains unknown."
    )
    title: str = Field(
        description="Nonblank article headline preserved as literal provider text."
    )
    source: str | None = Field(
        default=None,
        description="News site attribution supplied by the provider; missing attribution remains unknown.",
    )
    publisher: str | None = Field(
        default=None,
        description="Publisher attribution supplied by the provider, distinct from an identified journalist.",
    )
    author: str | None = Field(
        default=None,
        description="Journalist identity, unavailable from this endpoint and never inferred from publisher attribution.",
    )
    excerpt: str | None = Field(
        default=None,
        description="Literal provider excerpt, preserving whitespace and markup without claiming full article coverage.",
    )
    body: str | None = Field(
        default=None,
        description="Full article body, unavailable because this adapter does not retrieve article content.",
    )
    url: str = Field(
        description="Original public HTTP or HTTPS article link, retained without fetching the article."
    )
    symbols: str | None = Field(
        default=None,
        description="Standard news company linkage preserving the normalized requested listing symbol.",
    )
    images: Any | None = Field(
        default=None,
        description="Provider image metadata retained without retrieving or rendering remote image resources.",
    )
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: FinancialFieldTemplate(
                    value_origin="locally_derived"
                    if name == "content_status"
                    else "provider_observation",
                    source=_ORIGINS.get(name),
                    publication_date_field="date",
                )
                for name in [
                    "symbol",
                    "content_status",
                    "date",
                    "title",
                    "source",
                    "publisher",
                    "author",
                    "excerpt",
                    "body",
                    "url",
                    "symbols",
                    "images",
                ]
            },
            runtime_properties=[
                "fields.availability",
                "bounds",
                "effective_query",
                "retrieved_at",
            ],
        )
    )

    @field_validator("date", mode="before")
    @classmethod
    def publication_time(cls, value: Any) -> datetime:
        """Preserve source offset and naive timezone uncertainty."""
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?",
            value,
        ):
            raise ValueError("Publication timestamp syntax or precision is unsupported")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @field_validator("url")
    @classmethod
    def article_link(cls, value: str) -> str:
        """Keep literal public links without accepting active or credential URLs."""
        if (
            any(c.isspace() or ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
            or "\\" in value
        ):
            raise ValueError("Unsafe link")
        parts = urlsplit(value)
        if (
            parts.scheme.lower() not in ("http", "https")
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            raise ValueError("Unsafe link")
        parts.port  # Validate malformed ports without changing the supplied URL.
        return value


def _row(raw: Any, query: FMPCompanyNewsQueryParams) -> FMPCompanyNewsData:
    if not isinstance(raw, dict):
        raise FinancialError("invalid_response", provider="fmp")
    identity, text, title = raw.get("symbol"), raw.get("text"), raw.get("title")
    if (
        not isinstance(identity, str)
        or identity.upper() != query.symbol
        or (text is not None and not isinstance(text, str))
        or not isinstance(title, str)
        or not title.strip()
    ):
        raise FinancialError("invalid_response", provider="fmp")
    mapped = {name: raw[source] for name, source in _ORIGINS.items() if source in raw}
    mapped.update(
        symbol=query.symbol,
        symbols=query.symbol,
        author=None,
        body=None,
        content_status="partial" if text and text.strip() else "metadata_only",
    )
    return validate_financial_result(FMPCompanyNewsData, mapped, provider="fmp")


class FMPCompanyNewsFetcher(
    Fetcher[FMPCompanyNewsQueryParams, list[FMPCompanyNewsData]]
):
    """Fetch stock news once, without article, image or alternate-source retrieval."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCompanyNewsQueryParams:
        """Reject invalid company or paging choices before acquisition."""
        return validate_financial_query(
            FMPCompanyNewsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(
        query: FMPCompanyNewsQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Preserve the safe transport retrieval receipt."""
        from openbb_fmp.utils.helpers import get_data

        wire = dict(
            symbols=query.symbol,
            page=query.page,
            limit=query.limit,
            apikey=credentials.get("fmp_api_key", "") if credentials else "",
        )
        if query.start_date:
            wire.update(
                {"from": query.start_date.isoformat(), "to": query.end_date.isoformat()}
            )
        return await get_data(
            "https://financialmodelingprep.com/stable/news/stock?" + urlencode(wire),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query: FMPCompanyNewsQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPCompanyNewsData]]:
        """Validate the complete acquisition before clipping in source order."""
        if not isinstance(data.payload, list) or not data.payload:
            raise FinancialError("invalid_response", provider="fmp")
        rows = [_row(raw, query) for raw in data.payload]
        truncated = len(rows) > query.limit
        rows = rows[: query.limit]
        fields = render_field_templates(FMPCompanyNewsData)
        for name, field in fields.items():
            field.availability = (
                "available"
                if any(getattr(row, name) is not None for row in rows)
                else "missing"
            )
        metadata = FinancialResultMetadata(
            dataset="news/company",
            provider="fmp",
            retrieved_at=data.retrieved_at,
            source=FinancialSource(
                endpoint="news/stock",
                documentation="https://site.financialmodelingprep.com/developer/docs",
            ),
            effective_query=query.model_dump(mode="json"),
            fields=fields,
            publication_date_field="date",
            bounds=FinancialBounds(
                requested_limit=query.limit,
                effective_limit=query.limit,
                returned_count=len(rows),
                truncated=True if truncated else None,
                completeness="partial" if truncated else "unknown",
            ),
            limitations=[
                "Excerpts are partial; headlines alone are metadata-only.",
                "Publisher is attribution, not a journalist identity.",
                "Unsupplied publication timezone and exhaustive history are unknown.",
            ],
        )
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())
