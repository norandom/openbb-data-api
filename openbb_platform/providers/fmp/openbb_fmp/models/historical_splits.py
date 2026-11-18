"""Bounded historical splits adapted from retained FMP 1.6.1 declarations.

License: provider LICENSE and provenance.json. Retained source member SHA256:
070a03e8ee634c41743eb2e0da179af404a28fdaaf83ad214c0b98f4631011f5.
"""

import re
from datetime import date
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
from openbb_core.provider.standard_models.historical_splits import (
    HistoricalSplitsData,
    HistoricalSplitsQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPHistoricalSplitsQueryParams(HistoricalSplitsQueryParams):  # noqa: D101
    model_config = ConfigDict(extra="forbid", title="FrozenHistoricalSplitsQuery")
    __qopenbb_strict_admission__: ClassVar[bool] = True
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = (
        FinancialQueryAnnotation(
            provider_policy="explicit",
            procedural_bounds=ProceduralBounds(max_symbols=1),
            response_policy=ResponsePolicy(mode="clip", max_rows=100),
            runtime_properties=["bounds", "effective_query", "retrieved_at"],
        )
    )
    symbol: str = Field(min_length=1, max_length=50)

    @field_validator("symbol", mode="before")
    @classmethod
    def to_upper(cls, value):
        """Admit one listing identity without scalar coercion."""
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9^][A-Za-z0-9.^=-]{0,49}", value
        ):
            raise ValueError("One listing identity required")
        return value.upper()


def _template(shares=False):
    return FinancialFieldTemplate(
        unit="shares" if shares else None,
        value_origin="provider_observation",
        observation_date_field="date",
    )


class FMPHistoricalSplitsData(HistoricalSplitsData):  # noqa: D101
    model_config = ConfigDict(title="FrozenHistoricalSplitsData", allow_inf_nan=False)
    split_ratio: str | None = Field(
        None,
        title="Split Ratio",
        validation_alias="split_ratio",
        serialization_alias="split_ratio",
        description="Split ratio.",
    )
    numerator: float | None = Field(None, gt=0, description="New shares")
    denominator: float | None = Field(None, gt=0, description="Old shares")
    symbol: str = Field(description="Exact company listing identity.")
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _template(name in ("numerator", "denominator"))
                for name in (
                    "date",
                    "numerator",
                    "denominator",
                    "split_ratio",
                    "symbol",
                )
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def listing(cls, value):
        """Require an exact canonical source listing identity."""
        canonical = FMPHistoricalSplitsQueryParams.to_upper(value)
        if canonical != value:
            raise ValueError("Canonical listing identity required")
        return value

    @field_validator("date", mode="before")
    @classmethod
    def civil_date(cls, value):
        """Keep civil event dates separate from timestamps."""
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
        ):
            raise ValueError("Civil date required")
        return date.fromisoformat(value)

    @field_validator("numerator", "denominator", mode="before")
    @classmethod
    def components(cls, value):
        """Unknown components remain null; supplied components are positive numbers."""
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("Numeric component required")
        return value


class FMPHistoricalSplitsFetcher(
    Fetcher[FMPHistoricalSplitsQueryParams, list[FMPHistoricalSplitsData]]
):
    """Preserve source orientation and order without repricing historical observations."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPHistoricalSplitsQueryParams:
        """Validate native parameters before acquisition."""
        return validate_financial_query(
            FMPHistoricalSplitsQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Acquire once through the safe transport with its retrieval receipt."""
        from openbb_fmp.utils.helpers import get_data

        return await get_data(
            "https://financialmodelingprep.com/stable/splits?"
            + urlencode(
                {
                    "symbol": query.symbol,
                    "apikey": credentials.get("fmp_api_key", "") if credentials else "",
                }
            ),
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPHistoricalSplitsData]]:
        """Validate the entire acquisition before applying the local product cap."""
        if not isinstance(data.payload, list) or not data.payload:
            raise FinancialError("invalid_response", provider="fmp")
        rows = [_row(query, row) for row in data.payload]
        truncated = len(rows) > 100
        rows = rows[:100]
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data, truncated).as_metadata()
        )


def _row(query, row):
    if not isinstance(row, dict) or ("symbol" in row and row["symbol"] != query.symbol):
        raise FinancialError("invalid_response", provider="fmp")
    return validate_financial_result(
        FMPHistoricalSplitsData, {**row, "symbol": query.symbol}, provider="fmp"
    )


def _metadata(query, rows, data, truncated):
    fields = render_field_templates(FMPHistoricalSplitsData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/fundamental/historical_splits",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="splits",
            documentation="https://site.financialmodelingprep.com/developer/docs",
        ),
        effective_query={"symbol": query.symbol},
        fields=fields,
        observation_date_field="date",
        bounds=FinancialBounds(
            requested_limit=100,
            effective_limit=100,
            returned_count=len(rows),
            truncated=True if truncated else None,
            completeness="partial" if truncated else "unknown",
        ),
        limitations=[
            "Currency and adjustment methodology unknown.",
            "Civil event dates do not establish point-in-time availability.",
            "Product caps do not establish provider maxima or exhaustive history.",
        ],
    )
