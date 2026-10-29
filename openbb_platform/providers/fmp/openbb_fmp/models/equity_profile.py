"""FMP Equity Profile Model."""

# pylint: disable=unused-argument

from datetime import (
    date as dateType,
)
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.data import ForceInt
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_info import (
    EquityInfoData,
    EquityInfoQueryParams,
)
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
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_core.provider.utils.financial_errors import FinancialError
from openbb_core.provider.utils.financial_validation import validate_financial_result
from pydantic import ConfigDict, Field, field_validator, model_validator

from openbb_fmp.utils.helpers import FMPAcquisition


class FMPEquityProfileQueryParams(EquityInfoQueryParams):
    """FMP Equity Profile Query.

    Source: https://site.financialmodelingprep.com/developer/docs#profile-symbol
    """

    __json_schema_extra__: ClassVar[dict] = {"symbol": {"multiple_items_allowed": True}}
    financial_query_annotation: ClassVar[FinancialQueryAnnotation] = FinancialQueryAnnotation(
        provider_policy="baseline_default",
        response_policy=ResponsePolicy(mode="provider"),
        runtime_properties=["effective_query", "retrieved_at", "bounds"],
    )

    @field_validator("symbol", mode="after")
    @classmethod
    def normalize_symbols(cls, value: str) -> str:
        """Keep symbol identity while accepting whitespace around list items."""
        symbols = [symbol.strip() for symbol in value.split(",")]
        if any(not symbol for symbol in symbols):
            raise ValueError("Each requested symbol must be non-empty.")
        return ",".join(symbols)


class FMPEquityProfileData(EquityInfoData):
    """FMP Equity Profile Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "symbol": FinancialFieldTemplate(value_origin="provider_observation"),
            "name": FinancialFieldTemplate(value_origin="provider_observation"),
            "cik": FinancialFieldTemplate(value_origin="provider_observation"),
            "cusip": FinancialFieldTemplate(value_origin="provider_observation"),
            "isin": FinancialFieldTemplate(value_origin="provider_observation"),
            "lei": FinancialFieldTemplate(value_origin="provider_observation"),
            "legal_name": FinancialFieldTemplate(value_origin="provider_observation"),
            "stock_exchange": FinancialFieldTemplate(value_origin="provider_observation"),
            "sic": FinancialFieldTemplate(value_origin="provider_observation"),
            "short_description": FinancialFieldTemplate(value_origin="provider_observation"),
            "long_description": FinancialFieldTemplate(value_origin="provider_observation"),
            "ceo": FinancialFieldTemplate(value_origin="provider_observation"),
            "company_url": FinancialFieldTemplate(value_origin="provider_observation"),
            "business_address": FinancialFieldTemplate(value_origin="provider_observation"),
            "mailing_address": FinancialFieldTemplate(value_origin="provider_observation"),
            "business_phone_no": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_address1": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_address2": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_address_city": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_address_postal_code": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_state": FinancialFieldTemplate(value_origin="provider_observation"),
            "hq_country": FinancialFieldTemplate(value_origin="provider_observation"),
            "inc_state": FinancialFieldTemplate(value_origin="provider_observation"),
            "inc_country": FinancialFieldTemplate(value_origin="provider_observation"),
            "employees": FinancialFieldTemplate(unit="people", scale=1, value_origin="provider_observation"),
            "entity_legal_form": FinancialFieldTemplate(value_origin="provider_observation"),
            "entity_status": FinancialFieldTemplate(value_origin="provider_observation"),
            "latest_filing_date": FinancialFieldTemplate(value_origin="provider_observation"),
            "irs_number": FinancialFieldTemplate(value_origin="provider_observation"),
            "sector": FinancialFieldTemplate(value_origin="provider_observation"),
            "industry_category": FinancialFieldTemplate(value_origin="provider_observation"),
            "industry_group": FinancialFieldTemplate(value_origin="provider_observation"),
            "template": FinancialFieldTemplate(value_origin="provider_observation"),
            "standardized_active": FinancialFieldTemplate(value_origin="provider_observation"),
            "first_fundamental_date": FinancialFieldTemplate(value_origin="provider_observation"),
            "last_fundamental_date": FinancialFieldTemplate(value_origin="provider_observation"),
            "first_stock_price_date": FinancialFieldTemplate(value_origin="provider_observation"),
            "last_stock_price_date": FinancialFieldTemplate(value_origin="provider_observation"),
            "is_etf": FinancialFieldTemplate(value_origin="provider_observation"),
            "is_actively_trading": FinancialFieldTemplate(value_origin="provider_observation"),
            "is_adr": FinancialFieldTemplate(value_origin="provider_observation"),
            "is_fund": FinancialFieldTemplate(value_origin="provider_observation"),
            "image": FinancialFieldTemplate(value_origin="provider_observation"),
            "currency": FinancialFieldTemplate(value_origin="provider_observation"),
            "market_cap": FinancialFieldTemplate(
                unit="currency", scale=1, currency_field="currency", value_origin="provider_calculation"
            ),
            "last_price": FinancialFieldTemplate(
                unit="currency/share", scale=1, currency_field="currency", value_origin="provider_observation"
            ),
            "year_high": FinancialFieldTemplate(
                unit="currency/share", scale=1, currency_field="currency", value_origin="provider_observation"
            ),
            "year_low": FinancialFieldTemplate(
                unit="currency/share", scale=1, currency_field="currency", value_origin="provider_observation"
            ),
            "volume_avg": FinancialFieldTemplate(unit="shares", scale=1, value_origin="provider_calculation"),
            "annualized_dividend_amount": FinancialFieldTemplate(
                unit="currency/share", scale=1, currency_field="currency", value_origin="provider_calculation"
            ),
            "beta": FinancialFieldTemplate(unit="dimensionless", scale=1, value_origin="provider_calculation"),
        },
        runtime_properties=["fields.availability", "retrieved_at", "effective_query", "bounds"],
    )

    __alias_dict__: ClassVar[dict] = {
        "name": "companyName",
        "stock_exchange": "exchange",
        "company_url": "website",
        "hq_address1": "address",
        "hq_address_city": "city",
        "hq_address_postal_code": "zip",
        "hq_state": "state",
        "hq_country": "country",
        "business_phone_no": "phone",
        "industry_category": "industry",
        "employees": "fullTimeEmployees",
        "long_description": "description",
        "first_stock_price_date": "ipoDate",
        "last_price": "price",
        "volume_avg": "averageVolume",
        "annualized_dividend_amount": "lastDividend",
    }
    __json_schema_extra__: ClassVar[dict] = {"symbol": {"multiple_items_allowed": True}}
    model_config = ConfigDict(extra="ignore")

    is_etf: bool | None = Field(default=None, description="If the symbol is an ETF.")
    is_actively_trading: bool | None = Field(
        default=None, description="If the company is actively trading."
    )
    is_adr: bool | None = Field(default=None, description="If the stock is an ADR.")
    is_fund: bool | None = Field(default=None, description="If the company is a fund.")
    image: str | None = Field(default=None, description="Image of the company.")
    currency: str | None = Field(
        default=None, description="Currency in which the stock is traded."
    )
    market_cap: ForceInt | None = Field(
        default=None,
        description="Market capitalization of the company.",
    )
    last_price: float | None = Field(
        default=None,
        description="The last traded price.",
    )
    year_high: float | None = Field(
        default=None, description="The one-year high of the price."
    )
    year_low: float | None = Field(
        default=None, description="The one-year low of the price."
    )
    volume_avg: ForceInt | None = Field(
        default=None,
        description="Average daily trading volume.",
    )
    annualized_dividend_amount: float | None = Field(
        default=None,
        description="The annualized dividend payment based on the most recent regular dividend payment.",
    )
    beta: float | None = Field(
        default=None, description="Beta of the stock relative to the market."
    )

    @field_validator("first_stock_price_date", mode="before", check_fields=False)
    @classmethod
    def validate_date(cls, v):  # pylint: disable=E0213
        """Return the date as a datetime object."""
        if isinstance(v, dateType) or v is None:
            return v
        return dateType.fromisoformat(v) if v else None

    @model_validator(mode="before")
    @classmethod
    def replace_empty_strings(cls, values):
        """Check for empty strings and replace with None."""
        return (
            {k: None if v in ("", "NA") else v for k, v in values.items()}
            if isinstance(values, dict)
            else values
        )


class FMPEquityProfileFetcher(
    Fetcher[
        FMPEquityProfileQueryParams,
        list[FMPEquityProfileData],
    ]
):
    """FMP Equity Profile Fetcher."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPEquityProfileQueryParams:
        """Transform the query params."""
        return FMPEquityProfileQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FMPEquityProfileQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Return the raw data from the FMP endpoint."""
        # pylint: disable=import-outside-toplevel
        import asyncio  # noqa
        import warnings
        from openbb_fmp.utils.helpers import get_data

        api_key = credentials.get("fmp_api_key") if credentials else ""
        symbols = query.symbol.split(",")
        base_url = "https://financialmodelingprep.com/stable/"

        results: list = []
        acquisitions = []

        async def get_one(symbol):
            """Get data for one symbol."""
            params = urlencode({"symbol": symbol, "apikey": api_key})
            url = f"{base_url}profile?{params}"
            try:
                acquired = await get_data(url, with_provenance=True, typed_errors=False, **kwargs)
            except EmptyDataError:
                result = []
            else:
                acquisitions.append(acquired.retrieved_at)
                result = acquired.payload
            if not result:
                warnings.warn(f"Symbol Error: No data found for {symbol}")

            if result:
                if (not isinstance(result, list) or not isinstance(result[0], dict)
                        or result[0].get("symbol") != symbol):
                    raise FinancialError("invalid_response", provider="fmp")
                results.append(result[0])

        await asyncio.gather(*[get_one(symbol) for symbol in symbols])

        if not results:
            raise EmptyDataError("No data found for the given symbols.")

        return FMPAcquisition(
            sorted(results, key=lambda item: symbols.index(item["symbol"])),
            min(acquisitions),
        )

    @staticmethod
    def transform_data(
        query: FMPEquityProfileQueryParams,
        data: FMPAcquisition,
        **kwargs: Any,
    ) -> AnnotatedResult[list[FMPEquityProfileData]]:
        """Return the transformed data."""
        results: list[FMPEquityProfileData] = []

        for raw in data.payload:
            d = raw.copy()
            bounds = d.pop("range", None)
            if bounds is not None and not isinstance(bounds, str):
                raise FinancialError("invalid_response", provider="fmp")
            bounds = bounds.split("-") if bounds else [None, None]
            if len(bounds) != 2:
                raise FinancialError("invalid_response", provider="fmp")
            d["year_low"], d["year_high"] = bounds
            results.append(validate_financial_result(FMPEquityProfileData, d, provider="fmp"))

        metadata = _profile_metadata(query, results, data.retrieved_at)
        return AnnotatedResult(result=results, metadata=metadata.as_metadata())


def _profile_metadata(query, rows, retrieved_at):
    """Profile prices use each row's trading currency; quote dates are unavailable."""
    fields = render_field_templates(FMPEquityProfileData)
    for name, field in fields.items():
        field.availability = (
            "available" if any(getattr(row, name) is not None for row in rows) else "missing"
        )
    partial = len(rows) < len(query.symbol.split(","))
    return FinancialResultMetadata(
        dataset="equity/profile", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="profile"), effective_query={"symbol": query.symbol},
        fields=fields, bounds=FinancialBounds(returned_count=len(rows),
            truncated=None, completeness="partial" if partial else "unknown"),
        limitations=["Quote observation dates and provider coverage are unavailable.",
                     "Trading currency does not establish financial-statement currency."],
    )
