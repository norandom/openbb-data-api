"""Bounded filing metadata adapted from retained FMP 1.6.1 declarations.

License: provider LICENSE and provenance.json. Retained source member SHA256:
ab4c77778d5bfabdbbefd2b404b72b1e2e74d86d0b1521a2aaf5f10cf8c8fdf6.
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
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import (
    ConfigDict,
    Field,
    PrivateAttr,
    field_serializer,
    field_validator,
    model_validator,
)

from openbb_fmp.utils.helpers import FMPAcquisition

_ORIGINS = {
    "symbol": "symbol",
    "filing_date": "filingDate",
    "accepted_date": "acceptedDate",
    "report_type": "formType",
    "cik": "cik",
    "filing_url": "link",
    "report_url": "finalLink",
}
_DESCRIPTIONS = {
    "symbol": "Listing symbol identifying the requested company.",
    "content_status": "Inline content coverage; filings supply metadata only.",
    "filing_date": "Civil date on which the filing was made.",
    "accepted_date": "Source acceptance date or timestamp, preserving supplied precision and offset.",
    "report_type": "Source filing form type, including amendments when supplied.",
    "cik": "Source Central Index Key as a string preserving leading zeros.",
    "filing_url": "Source filing index URL; the index is not retrieved.",
    "report_url": "Source report document URL; the document is not retrieved.",
}


class FMPCompanyFilingsQueryParams(QueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="FrozenCompanyFilingsQuery")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date
    page: int = Field(0, strict=True, ge=0, le=99)
    limit: int = Field(20, strict=True, ge=1, le=100)

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
    def inclusive_window(self) -> Self:
        """Bound the required filing window to 365 inclusive civil dates."""
        if not 0 <= (self.end_date - self.start_date).days < 365:
            raise ValueError("Invalid inclusive window")
        return self


class FMPCompanyFilingsData(Data):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="Filing", alias_generator=None)
    symbol: str = Field(description=_DESCRIPTIONS["symbol"])
    content_status: Literal[
        "partial", "metadata_only", "completeness_unknown", "full"
    ] = Field(description=_DESCRIPTIONS["content_status"])
    filing_date: date = Field(description=_DESCRIPTIONS["filing_date"])
    accepted_date: datetime | date | None = Field(
        None, description=_DESCRIPTIONS["accepted_date"]
    )
    report_type: str | None = Field(None, description=_DESCRIPTIONS["report_type"])
    cik: str | None = Field(None, description=_DESCRIPTIONS["cik"])
    filing_url: str | None = Field(None, description=_DESCRIPTIONS["filing_url"])
    report_url: str = Field(description=_DESCRIPTIONS["report_url"])
    _accepted_lexeme: str | None = PrivateAttr(default=None)
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: FinancialFieldTemplate(
                    definition=_DESCRIPTIONS[name],
                    value_origin="locally_derived"
                    if name == "content_status"
                    else "provider_observation",
                    source=_ORIGINS.get(name),
                    publication_date_field="filing_date",
                )
                for name in [
                    "symbol",
                    "content_status",
                    "filing_date",
                    "accepted_date",
                    "report_type",
                    "cik",
                    "filing_url",
                    "report_url",
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

    @field_validator("filing_date", mode="before")
    @classmethod
    def filing_day(cls, value: Any) -> date:
        """Filing dates carry civil dates without a synthesized clock."""
        return FMPCompanyFilingsQueryParams.civil_bound(value)

    @field_validator("accepted_date", mode="before")
    @classmethod
    def acceptance_time(cls, value: Any) -> datetime | date | None:
        """Retain date-only values and supplied clocks, offsets and naive times."""
        if value is None or isinstance(value, (datetime, date)):
            return value
        if not isinstance(value, str):
            raise ValueError("Acceptance date or timestamp required")
        if len(value) == 10:
            return FMPCompanyFilingsQueryParams.civil_bound(value)
        if not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?",
            value,
        ):
            raise ValueError("Unsupported acceptance timestamp precision or spelling")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @model_validator(mode="wrap")
    @classmethod
    def retain_acceptance_lexeme(cls, value, handler):
        """Retain fractional width and supplied offset spelling beside the typed value."""
        row = handler(value)
        if isinstance(value, dict) and isinstance(value.get("accepted_date"), str):
            row._accepted_lexeme = value["accepted_date"]
        return row

    @field_serializer("accepted_date", when_used="json")
    def serialize_acceptance(self, value):
        """Avoid padding fractions or converting an unknown zero offset into UTC."""
        if self._accepted_lexeme is not None and value is not None:
            parser = datetime if isinstance(value, datetime) else date
            original = parser.fromisoformat(self._accepted_lexeme)
            if original.isoformat() == value.isoformat():
                return self._accepted_lexeme
        return value

    @field_validator("filing_url", "report_url")
    @classmethod
    def document_link(cls, value: str | None) -> str | None:
        """Keep literal public links without accepting active or credential URLs."""
        if value is None:
            return value
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


def _row(raw: Any, query: FMPCompanyFilingsQueryParams) -> FMPCompanyFilingsData:
    if not isinstance(raw, dict):
        raise FinancialError("invalid_response", provider="fmp")
    identity = raw.get("symbol")
    if not isinstance(identity, str) or identity.upper() != query.symbol:
        raise FinancialError("invalid_response", provider="fmp")
    mapped = {name: raw[source] for name, source in _ORIGINS.items() if source in raw}
    filing_date = mapped.get("filing_date")
    # FMP pads its civil filing date with midnight; this is not an acceptance clock.
    if isinstance(filing_date, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2} 00:00:00", filing_date
    ):
        mapped["filing_date"] = filing_date[:10]
    mapped.update(symbol=query.symbol, content_status="metadata_only")
    return validate_financial_result(FMPCompanyFilingsData, mapped, provider="fmp")


class FMPCompanyFilingsFetcher(
    Fetcher[FMPCompanyFilingsQueryParams, list[FMPCompanyFilingsData]]
):
    """Fetch filing metadata once; document bodies are never retrieved."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPCompanyFilingsQueryParams:
        """Reject invalid company or paging choices before acquisition."""
        return validate_financial_query(
            FMPCompanyFilingsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(
        query: FMPCompanyFilingsQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Preserve the safe transport retrieval receipt."""
        from openbb_fmp.utils.helpers import get_data

        wire = dict(
            symbol=query.symbol,
            page=query.page,
            limit=query.limit,
            apikey=credentials.get("fmp_api_key", "") if credentials else "",
        )
        if query.start_date:
            wire.update(
                {"from": query.start_date.isoformat(), "to": query.end_date.isoformat()}
            )
        return await get_data(
            "https://financialmodelingprep.com/stable/sec-filings-search/symbol?"
            + urlencode(wire),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query: FMPCompanyFilingsQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPCompanyFilingsData]]:
        """Validate the complete acquisition before clipping in source order."""
        if not isinstance(data.payload, list) or not data.payload:
            raise FinancialError("invalid_response", provider="fmp")
        rows = [_row(raw, query) for raw in data.payload]
        truncated = len(rows) > query.limit
        rows = rows[: query.limit]
        fields = {
            name: FinancialFieldMetadata(
                **template.model_dump(exclude={"availability"}),
                availability="available"
                if any(getattr(row, name) is not None for row in rows)
                else "missing",
            )
            for name, template in FMPCompanyFilingsData.financial_data_annotation.fields.items()
        }
        metadata = FinancialResultMetadata(
            dataset="equity/fundamental/filings",
            provider="fmp",
            retrieved_at=data.retrieved_at,
            source=FinancialSource(
                endpoint="sec-filings-search/symbol",
                documentation="https://site.financialmodelingprep.com/developer/docs",
            ),
            effective_query=query.model_dump(mode="json"),
            fields=fields,
            publication_date_field="filing_date",
            bounds=FinancialBounds(
                requested_limit=query.limit,
                effective_limit=query.limit,
                returned_count=len(rows),
                truncated=True if truncated else None,
                completeness="partial" if truncated else "unknown",
            ),
            limitations=[
                "Filing metadata only; document and index links are not retrieved.",
                "Unsupplied acceptance timezone and exhaustive history are unknown.",
            ],
        )
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())
