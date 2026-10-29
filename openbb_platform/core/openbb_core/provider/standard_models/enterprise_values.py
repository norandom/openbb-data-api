"""Provider-reported enterprise-value inputs without analyst adjustments."""

from datetime import date as dateType
from typing import Literal

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import ConfigDict, Field


class EnterpriseValuesQueryParams(QueryParams):
    """Bound periodic enterprise-value input observations for one listing."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(description="One provider listing symbol.")
    period: Literal["annual", "quarter"] = Field(default="annual", description="Requested source frequency; not a market-date guarantee.")
    limit: int = Field(default=5, ge=1, le=1000, strict=True, description="Maximum records, 1 through 1000.")


class EnterpriseValuesData(Data):
    """Keep dates and currency only when supplied; component conventions may be unknown."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    symbol: str = Field(description="Provider listing identity.")
    date: dateType | None = Field(default=None, description="Provider observation date; not proof of market-input as-of date.")
    currency: str | None = Field(default=None, description="Reported row currency when explicitly supplied; never inferred.")
    stock_price: float | None = Field(default=None, description="Provider share price in row currency per share; adjustment and market date unknown.")
    number_of_shares: float | None = Field(default=None, description="Provider share count in shares; basic, diluted and treasury-stock bases unknown.")
    market_cap: float | None = Field(default=None, description="Provider market capitalization in row currency; share and price-date basis unknown.")
    cash_and_cash_equivalents: float | None = Field(default=None, description="Provider cash component in row currency; restriction and netting conventions unknown.")
    total_debt: float | None = Field(default=None, description="Provider debt component in row currency; lease inclusion and netting conventions unknown.")
    enterprise_value: float | None = Field(default=None, description="Provider-calculated enterprise value in row currency, without local bridge or adjustments.")
