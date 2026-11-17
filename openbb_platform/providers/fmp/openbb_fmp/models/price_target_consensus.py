"""FMP consensus estimates preserve distinct statistics and unknown vintage."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# e2cb2c40609d96f7358096b6f690acdff576268827cb6ec09ec88bc34a06e14e.
import re
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
from openbb_core.provider.standard_models.price_target_consensus import (
    PriceTargetConsensusData,
    PriceTargetConsensusQueryParams,
)
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import (
    validate_financial_query,
    validate_financial_result,
)
from pydantic import ConfigDict, Field, field_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPPriceTargetConsensusQueryParams(PriceTargetConsensusQueryParams):  # noqa: D101
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
        description="One provider listing identity; at most one matching response.",
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


def _consensus_template(name):
    monetary = name.startswith("target_")
    return FinancialFieldTemplate(
        unit="currency/share" if monetary else None,
        scale=1 if monetary else None,
        value_origin="estimate" if monetary else "provider_observation",
        financial_basis={"market_date": None, "forecast_period": None},
    )


class FMPPriceTargetConsensusData(PriceTargetConsensusData):
    """FMP Price Target Consensus Data."""

    model_config = ConfigDict(allow_inf_nan=False)
    financial_data_annotation: ClassVar[FinancialDataAnnotation] = (
        FinancialDataAnnotation(
            fields={
                name: _consensus_template(name)
                for name in PriceTargetConsensusData.model_fields
            },
            runtime_properties=[
                "fields.availability",
                "retrieved_at",
                "effective_query",
                "bounds",
            ],
        )
    )

    @field_validator(
        "target_high", "target_low", "target_consensus", "target_median", mode="before"
    )
    @classmethod
    def finite_estimate(cls, value):
        """Keep nulls and zero distinct and reject malformed estimates."""
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError("Invalid target estimate")
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise ValueError("Invalid target estimate") from None
        if not isfinite(number):
            raise ValueError("Invalid target estimate")
        return number


class FMPPriceTargetConsensusFetcher(
    Fetcher[FMPPriceTargetConsensusQueryParams, list[FMPPriceTargetConsensusData]]
):
    """Request one listing consensus without synthesizing missing statistics."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPPriceTargetConsensusQueryParams:
        """Reject malformed raw queries before acquisition."""
        return validate_financial_query(
            FMPPriceTargetConsensusQueryParams, params, provider="fmp"
        )

    @staticmethod
    async def aextract_data(query, credentials, **kwargs: Any) -> FMPAcquisition:
        """Use the shared typed transport and its actual acquisition timestamp."""
        from openbb_fmp.utils.helpers import get_data_many

        params = query.model_dump()
        params["apikey"] = credentials.get("fmp_api_key", "") if credentials else ""
        return await get_data_many(
            "https://financialmodelingprep.com/stable/price-target-consensus?"
            + urlencode(params),
            allow_empty=True,
            with_provenance=True,
            typed_errors=True,
            **kwargs,
        )

    @staticmethod
    def transform_data(
        query, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPPriceTargetConsensusData]]:
        """Reject ambiguous response identity instead of picking a first row."""
        rows = [
            validate_financial_result(FMPPriceTargetConsensusData, row, provider="fmp")
            for row in data.payload
        ]
        if len(rows) > 1 or any(row.symbol != query.symbol for row in rows):
            raise FinancialError("invalid_response", provider="fmp")
        return AnnotatedResult(
            result=rows, metadata=_metadata(query, rows, data).as_metadata()
        )


def _metadata(query, rows, data):
    fields = render_field_templates(FMPPriceTargetConsensusData)
    for name, field in fields.items():
        field.availability = (
            "available"
            if any(getattr(row, name) is not None for row in rows)
            else "missing"
        )
    return FinancialResultMetadata(
        dataset="equity/estimates/consensus",
        provider="fmp",
        retrieved_at=data.retrieved_at,
        source=FinancialSource(
            endpoint="price-target-consensus",
            documentation="https://site.financialmodelingprep.com/developer/docs/stable/price-target-consensus",
        ),
        effective_query=query.model_dump(),
        fields=fields,
        bounds=FinancialBounds(returned_count=len(rows), completeness="unknown"),
        limitations=[
            "No retained date or currency field: as-of, membership and lineage unknown; not point-in-time safe.",
            "Official FAQ checked 2026-11-17: six-month window, latest target per analyst company, daily recomputation; response-specific methodology not verified.",
            "Approved request caps are local conservative policies, not verified FMP maxima. One upstream call; live entitlement and consumer acceptance unverified.",
        ],
    )
