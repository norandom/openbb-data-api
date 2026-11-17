"""FMP analyst events preserve publication precision and separate target estimates."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# ed03eb37a82fd6c3b413c6dc99c8f02417b25fca7afcb4507daebe96b63a22df.
import re
from datetime import date, datetime, time
from math import isfinite
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
    FinancialQueryAnnotation,
    ProceduralBounds,
    ResponsePolicy,
    render_field_templates,
)
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.standard_models.price_target import (
    PriceTargetData,
    PriceTargetQueryParams,
)
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPPriceTargetQueryParams(PriceTargetQueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", limit_parameter="limit"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        max_length=50,
        description="One provider listing identity; maximum 50 characters.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        strict=True,
        description="Maximum news events; one upstream request and no public page.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Validate one listing before native optional-symbol normalization."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("One symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("One symbol is required")
        return value


def _event_template(name):
    monetary = name in {
        "price_target",
        "adj_price_target",
        "price_target_previous",
        "previous_adj_price_target",
        "price_when_posted",
    }
    return FinancialFieldTemplate(
        unit="currency/share" if monetary else None,
        scale=1 if monetary else None,
        currency_field="currency" if monetary else None,
        value_origin=(
            "estimate"
            if monetary and name != "price_when_posted"
            else "provider_observation"
        ),
        publication_date_field="published_date",
        financial_basis={"market_date": None},
    )


class FMPPriceTargetData(PriceTargetData):
    """FMP Price Target Data."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    __alias_dict__ = {
        "analyst_firm": "analystCompany",
        "rating_current": "newGrade",
        "rating_previous": "previousGrade",
        "news_title": "newsTitle",
        "news_url": "newsURL",
    }
    news_title: str | None = Field(
        default=None, description="News title of the price target."
    )
    news_url: str | None = Field(
        default=None, description="News URL of the price target."
    )
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _event_template(name)
                for name in [
                    *PriceTargetData.model_fields,
                    "news_title",
                    "news_url",
                ]
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("published_date", mode="before")
    @classmethod
    def publication_date(cls, value):
        """Parse calendar dates separately so midnight timestamps retain their type."""
        if isinstance(value, datetime) or type(value) is date:
            return value
        if isinstance(value, str):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                return date.fromisoformat(value)
            if re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
                return datetime.fromisoformat(value)
        raise ValueError("Publication date or timestamp required")

    @field_validator("published_time", mode="before")
    @classmethod
    def publication_time(cls, value):
        """Do not infer UTC or extract a missing publication time from retrieval."""
        if value is None or isinstance(value, time):
            return value
        if isinstance(value, str) and re.match(r"\d{2}:\d{2}", value):
            return time.fromisoformat(value)
        raise ValueError("Publication time required when provided")

    @field_validator(
        "price_target",
        "adj_price_target",
        "price_target_previous",
        "previous_adj_price_target",
        "price_when_posted",
        mode="before",
    )
    @classmethod
    def monetary_value(cls, value):
        """Reject boolean and non-finite prices while preserving nulls and zero."""
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError("Invalid target or posted price")
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise ValueError("Invalid target or posted price") from None
        if not isfinite(number):
            raise ValueError("Invalid target or posted price")
        return number


class FMPPriceTargetFetcher(
    Fetcher[FMPPriceTargetQueryParams, list[FMPPriceTargetData]]
):
    """Request one bounded news page without sorting or collapsing analyst events."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPPriceTargetQueryParams:
        """Reject malformed raw queries before acquisition."""
        return validate_financial_query(
            FMPPriceTargetQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the shared typed transport and its actual acquisition timestamp."""
        from openbb_fmp.utils.helpers import get_data_many

        params = query.model_dump()
        params["apikey"] = credentials.get("fmp_api_key", "") if credentials else ""
        return await get_data_many(
            "https://financialmodelingprep.com/stable/price-target-news?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPPriceTargetData]]:
        """Validate source rows before clipping; duplicate dates remain distinct events."""
        rows = [
            validate_financial_result(FMPPriceTargetData, row, provider="fmp")
            for row in data.payload
        ]
        truncated = len(rows) > query.limit
        rows = rows[: query.limit]
        return AnnotatedResult(
            result=rows,
            metadata=_metadata(query, rows, data, truncated).as_metadata(),
        )


def _metadata(query, rows, data, truncated):
    fields = render_field_templates(FMPPriceTargetData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/estimates/price_target",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="price-target-news",
            documentation="https://site.financialmodelingprep.com/education/other/price-target-news-api-endpoint-make-smarter-buy-or-sell-decisions",
        ),
        effective_query=query.model_dump(),
        fields=fields,
        publication_date_field="published_date",
        bounds=FinancialBounds(
            requested_limit=query.limit,
            effective_limit=query.limit,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Publication dates and times preserve source precision and timezone; absent time or timezone is unknown.",
            "Targets are analyst estimates; posted prices are provider observations, with market-date and adjustment bases unknown where absent.",
            "Currency is unknown where absent; prices retain provider scale 1 in currency per share.",
            "Provider row order and distinct analyst events are preserved; publication does not establish historical vintage or point-in-time safety.",
            "Official education examples document symbol and limit; dedicated endpoint documentation and live entitlement remain unverified.",
            "One request without public pagination; total completeness is unknown unless local clipping proves partial output.",
        ],
    )
