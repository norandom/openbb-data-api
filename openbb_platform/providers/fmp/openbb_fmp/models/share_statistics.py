"""FMP shares-float observations, adapted from the retained 1.6.1 source.

SPDX-License-Identifier: AGPL-3.0-only
License notice: provider LICENSE and provenance.json.
Source member SHA256 529f6cdf6e2e07edad94f9b23740793b36b39052444d0c63bc7127d616c63bf6.
"""

import re
from datetime import date, datetime
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
from openbb_core.provider.standard_models.share_statistics import (
    ShareStatisticsData,
    ShareStatisticsQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPShareStatisticsQueryParams(ShareStatisticsQueryParams):


    model_config = ConfigDict(extra="forbid")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="provider"),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(
        max_length=50,
        description="One provider listing identity; maximum 50 characters.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Reject ambiguous identities and query syntax before transport."""
        if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("One symbol is required")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^_/-]{0,49}", value):
            raise ValueError("One symbol is required")
        return value


def _template(unit=None):
    return FinancialFieldTemplate(
        unit=unit,
        scale=1 if unit else None,
        value_origin="provider_calculation" if unit == "ratio" else "provider_observation",
        observation_date_field="date",
        source_unit="percent" if unit == "ratio" else None,
        requested_transform="divide_by_100" if unit == "ratio" else None,
        financial_basis={
            "share_count": "provider float and outstanding share counts; methodology unknown"
        },
    )


class FMPShareStatisticsData(ShareStatisticsData):


    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    __alias_dict__ = {"url": "source"}
    url: str | None = Field(
        default=None, description="URL to the source document, if available."
    )
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                "symbol": _template(),
                "date": _template(),
                "free_float": _template("ratio"),
                "float_shares": _template("shares"),
                "outstanding_shares": _template("shares"),
                "url": _template(),
            },
            runtime_properties=[
                "fields.availability", "retrieved_at", "effective_query", "bounds"
            ],
        )
    )

    @field_validator("free_float", "float_shares", "outstanding_shares", mode="before")
    @classmethod
    def numeric_facts(cls, value):
        """Counts and percentages cannot be booleans or coerced strings."""
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("Numeric source fact required")
        return value

    @field_validator("free_float", mode="after")
    @classmethod
    def normalize_percent(cls, value):
        """Convert the provider percentage to a ratio, preserving zero and null."""
        return value / 100 if value is not None else None

    @field_validator("date", mode="before")
    @classmethod
    def source_date(cls, value):
        """Retain nullable source precision without inventing a retrieval date."""
        if value is None or isinstance(value, (date, datetime)):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[Tt ].+)?", value):
            raise ValueError("Source date required")
        return value


class FMPShareStatisticsFetcher(
    Fetcher[FMPShareStatisticsQueryParams, list[FMPShareStatisticsData]]
):
    """Acquire one shares-float response without inference or fan-out."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPShareStatisticsQueryParams:
        """Expose safe parameter errors before I/O."""
        return validate_financial_query(FMPShareStatisticsQueryParams, params, provider="fmp")

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Retain the shared transport's receipt and typed failure policy."""
        from openbb_fmp.utils.helpers import get_data_many

        params = {
            "symbol": query.symbol,
            "apikey": credentials.get("fmp_api_key", "") if credentials else "",
        }
        return await get_data_many(
            "https://financialmodelingprep.com/stable/shares-float?" + urlencode(params),
            with_provenance=True,
            typed_errors=True,
            allow_empty=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(query, data: FMPAcquisition, **kwargs: Any):
        """Reject ambiguous or foreign identities rather than selecting a row."""
        rows = [
            validate_financial_result(FMPShareStatisticsData, row, provider="fmp")
            for row in data.payload
        ]
        if len(rows) > 1 or any(row.symbol != query.symbol for row in rows):
            raise FinancialError("invalid_response", provider="fmp") from None
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data).as_metadata()
        )


def _metadata(query, rows, data):
    fields = render_field_templates(FMPShareStatisticsData)
    for name, field in fields.items():
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/ownership/share_statistics",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="shares-float",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/shares-float",
        ),
        effective_query={"symbol": query.symbol},
        fields=fields,
        observation_date_field="date",
        bounds=FinancialBounds(returned_count=len(rows), completeness="unknown"),
        limitations=[
            "Float and outstanding counts are provider observations; methodology is unknown.",
            "Free float is the provider percentage divided by 100; no count basis is inferred.",
            "Publication dates, vintage and restatements are unknown; not point-in-time safe.",
            "Source observation date may be unavailable; retrieval time is not substituted.",
        ],
    )


