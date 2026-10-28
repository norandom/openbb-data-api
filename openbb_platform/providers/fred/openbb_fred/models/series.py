"""FRED Series Model."""

from typing import Any, Literal

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_metadata import (
    FINANCIAL_METADATA_KEY,
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialResultMetadata,
    FinancialSource,
    FinancialTransformation,
)
from openbb_core.provider.standard_models.fred_series import (
    SeriesData,
    SeriesQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_fred.utils.query import UseCacheQueryParams
from pydantic import Field, field_validator


class FredSeriesQueryParams(UseCacheQueryParams, SeriesQueryParams):
    """FRED Series Query Params."""

    @field_validator("symbol", mode="before")
    @classmethod
    def reserved_namespace(cls, value: str) -> str:
        """Reject the reserved namespace before FRED normalizes ID casing."""
        if any(item.casefold() == FINANCIAL_METADATA_KEY for item in value.split(",")):
            raise ValueError("Series identifier is reserved")
        return value

    __alias_dict__ = {
        "symbol": "series_id",
        "start_date": "observation_start",
        "end_date": "observation_end",
        "transform": "units",
    }
    __json_schema_extra__ = {
        "symbol": {"multiple_items_allowed": True},
    }

    frequency: (
        Literal[
            "a",
            "q",
            "m",
            "w",
            "d",
            "wef",
            "weth",
            "wew",
            "wetu",
            "wem",
            "wesu",
            "wesa",
            "bwew",
            "bwem",
        ]
        | None
    ) = Field(
        default=None,
        description="""Frequency aggregation to convert high frequency data to lower frequency.
    None = No change
    a = Annual
    q = Quarterly
    m = Monthly
    w = Weekly
    d = Daily
    wef = Weekly, Ending Friday
    weth = Weekly, Ending Thursday
    wew = Weekly, Ending Wednesday
    wetu = Weekly, Ending Tuesday
    wem = Weekly, Ending Monday
    wesu = Weekly, Ending Sunday
    wesa = Weekly, Ending Saturday
    bwew = Biweekly, Ending Wednesday
    bwem = Biweekly, Ending Monday""",
    )
    aggregation_method: Literal["avg", "sum", "eop"] | None = Field(
        default="eop",
        description="""A key that indicates the aggregation method used for frequency aggregation.
        This parameter has no affect if the frequency parameter is not set.
        avg = Average
        sum = Sum
        eop = End of Period
        """,
    )
    transform: (
        Literal["chg", "ch1", "pch", "pc1", "pca", "cch", "cca", "log"] | None
    ) = Field(
        default=None,
        description="""Transformation type
    None = No transformation
    chg = Change
    ch1 = Change from Year Ago
    pch = Percent Change
    pc1 = Percent Change from Year Ago
    pca = Compounded Annual Rate of Change
    cch = Continuously Compounded Rate of Change
    cca = Continuously Compounded Annual Rate of Change
    log = Natural Log""",
    )
    limit: int = Field(description=QUERY_DESCRIPTIONS.get("limit", ""), default=100000)


class FredSeriesData(SeriesData):
    """FRED Series Data."""


class FredSeriesFetcher(
    Fetcher[
        FredSeriesQueryParams,
        list[FredSeriesData],
    ]
):
    """FRED Series Fetcher."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FredSeriesQueryParams:
        """Transform query."""
        return FredSeriesQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FredSeriesQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract data."""
        import asyncio

        from openbb_fred.utils.api import build_url
        from openbb_fred.utils.rate_limiter import fred_get
        from openbb_fred.utils.response import observations
        from pandas import DataFrame

        api_key = credentials.get("fred_api_key") if credentials else ""
        params = query.model_dump(exclude_none=True)
        params.pop("series_id", None)
        params.pop("use_cache", None)
        series_ids = query.symbol.split(",") if "," in query.symbol else [query.symbol]

        async def fetch_one(series_id: str) -> dict:
            obs_url = build_url(
                "series/observations", api_key, series_id=series_id, **params
            )
            meta_url = build_url("series", api_key, series_id=series_id)

            observations_response = await fred_get(
                obs_url, timeout=5, use_cache=query.use_cache, with_provenance=True, **kwargs
            )
            metadata_response = await fred_get(
                meta_url, timeout=5, use_cache=query.use_cache, with_provenance=True, **kwargs
            )

            _metadata = (
                metadata_response.payload.get("seriess", [{}])[0]
                if isinstance(metadata_response.payload, dict)
                else {}
            ) or {}
            rows = observations(observations_response.payload)
            provenance = {
                row["date"]: {key: row.get(key) for key in ("realtime_start", "realtime_end")}
                for row in rows if "date" in row
            }

            try:
                data = (
                    DataFrame(rows)
                    .replace(".", None)
                    .set_index("date")["value"]
                    .astype(float)
                    .to_dict()
                ) if rows else {}
            except (KeyError, TypeError):
                raise OpenBBError("FRED request failed.") from None

            return {
                series_id: {
                    "title": _metadata.get("title"),
                    "units": _metadata.get("units"),
                    "frequency": _metadata.get("frequency"),
                    "seasonal_adjustment": _metadata.get("seasonal_adjustment"),
                    "notes": _metadata.get("notes"),
                    "data": data,
                    "_retrieved_at": min(observations_response.retrieved_at, metadata_response.retrieved_at),
                    "_provenance": provenance,
                }
            }

        try:
            results: list[dict] = []
            for result in await asyncio.gather(
                *[fetch_one(sid) for sid in series_ids], return_exceptions=True
            ):
                if isinstance(result, BaseException):
                    raise result
                if result:
                    results.append(result)
            return results
        except OpenBBError as error:
            from openbb_fred.utils.response import safe_error
            raise safe_error(error) from None
        except Exception:
            raise OpenBBError("FRED request failed.") from None

    @staticmethod
    def transform_data(
        query: FredSeriesQueryParams, data: list[dict], **kwargs: Any
    ) -> AnnotatedResult[list[FredSeriesData]]:
        """Transform data."""
        from pandas import DataFrame  # noqa
        from numpy import nan

        series = {_id: s.get("data", {}) for d in data for _id, s in d.items()}
        metadata = {
            _id: {key: value for key, value in m.items() if key not in ("data", "_retrieved_at", "_provenance")}
            for d in data for _id, m in d.items()
        }
        records = (
            DataFrame(series)
            .filter(items=query.symbol.split(","), axis=1)
            .sort_index()
            .reset_index()
            .rename(columns={"index": "date"})
            .replace({nan: None})
            .to_dict("records")
        )
        validated = [FredSeriesData.model_validate(r) for r in records]
        common = _financial_metadata(query, data, len(validated))
        return AnnotatedResult(result=validated, metadata=common.as_metadata(metadata))


_FREQUENCIES = {
    "a": "Annual", "q": "Quarterly", "m": "Monthly", "w": "Weekly", "d": "Daily",
    "wef": "Weekly, Ending Friday", "weth": "Weekly, Ending Thursday",
    "wew": "Weekly, Ending Wednesday", "wetu": "Weekly, Ending Tuesday",
    "wem": "Weekly, Ending Monday", "wesu": "Weekly, Ending Sunday",
    "wesa": "Weekly, Ending Saturday", "bwew": "Biweekly, Ending Wednesday",
    "bwem": "Biweekly, Ending Monday",
}
_PERCENT_UNITS = {"pch": "Percent Change", "pc1": "Percent Change from Year Ago"}


def _field_metadata(query: FredSeriesQueryParams, metadata: dict) -> FinancialFieldMetadata:
    """Separate source measures from provider calculations on those measures."""
    unit = metadata.get("units") if query.transform is None else _PERCENT_UNITS.get(query.transform)
    return FinancialFieldMetadata(
        definition=metadata.get("title") or "FRED economic/benchmark series observation",
        unit=unit,
        source="fred",
        source_unit=metadata.get("units"),
        source_frequency=metadata.get("frequency"),
        effective_frequency=_FREQUENCIES.get(query.frequency) if query.frequency else metadata.get("frequency"),
        seasonal_adjustment=metadata.get("seasonal_adjustment"),
        requested_transform=query.transform,
        aggregation=query.aggregation_method if query.frequency else None,
        value_origin="provider_calculation" if query.transform or query.frequency else "provider_observation",
        observation_date_field="date",
    )


def _transformations(query: FredSeriesQueryParams, fields: list[str]) -> list[FinancialTransformation]:
    """Describe requested provider operations without recomputing observations."""
    operations = []
    if query.frequency:
        operations.append(FinancialTransformation(
            name="frequency_aggregation", affected_fields=fields,
            source_basis="Each series source frequency and units",
            definition=f"FRED frequency={query.frequency}, aggregation_method={query.aggregation_method}; provider aggregation only.",
        ))
    if query.transform:
        operations.append(FinancialTransformation(
            name="fred_units_transform", affected_fields=fields,
            source_basis="Each series source observations; FRED performs the requested units transformation",
            definition={"pch": "100 * (value / prior-period value - 1)",
                        "pc1": "100 * (value / year-ago value - 1)"}.get(
                            query.transform, f"FRED units={query.transform}; effective unit convention unestablished"),
        ))
    return operations


def _financial_metadata(query: FredSeriesQueryParams, data: list[dict], count: int) -> FinancialResultMetadata:
    """Use the oldest component acquisition; real-time intervals do not prove PIT safety."""
    components = {series_id: value for item in data for series_id, value in item.items()}
    limitations = [
        "Historical vintage-query capability and publication dates are unknown; real-time intervals do not establish point-in-time safety.",
        "Wide columns align observation dates without interpolation or implicit frequency conversion.",
        "Provider result completeness is unknown.",
    ]
    if query.transform and query.transform not in _PERCENT_UNITS:
        limitations.append(f"Effective unit for FRED transform {query.transform} is unknown.")
    return FinancialResultMetadata(
        dataset="economy.fred_series", provider="fred",
        retrieved_at=min(value["_retrieved_at"] for value in components.values()),
        source=FinancialSource(endpoint="series/observations", documentation="https://fred.stlouisfed.org/docs/api/fred/series_observations.html"),
        effective_query={**query.model_dump(mode="json", exclude_none=True), "symbol": query.symbol},
        fields={series_id: _field_metadata(query, value) for series_id, value in components.items()},
        bounds=FinancialBounds(requested_limit=query.limit, returned_count=count),
        limitations=limitations,
        transformations=_transformations(query, list(components)),
        observation_date_field="date",
        observation_provenance={series_id: value["_provenance"] for series_id, value in components.items()},
    )
