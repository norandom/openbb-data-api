"""Retained periodic key-metric fields; values remain provider calculations."""

from typing import ClassVar

from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from openbb_core.provider.standard_models.key_metrics import KeyMetricsData
from pydantic import ConfigDict, Field, model_validator


def _calculation(unit: str) -> FinancialFieldTemplate:
    """Declare provider calculations without assuming valuation conventions."""
    return FinancialFieldTemplate(
        unit=unit, scale=1, value_origin="provider_calculation",
        currency_field="currency" if unit in {"currency", "currency/share"} else None,
        financial_basis={
            "share_count": None, "debt": None, "cash": None, "lease": None,
            "minority_interest": None, "forecast_period": None, "market_date": None,
        },
    )


class FMPKeyMetricsData(KeyMetricsData):
    """FMP Equity Valuation Multiples Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "symbol": FinancialFieldTemplate(
                value_origin="provider_observation", observation_date_field="period_ending"
            ),
            "period_ending": FinancialFieldTemplate(
                value_origin="provider_observation", observation_date_field="period_ending"
            ),
            "fiscal_year": FinancialFieldTemplate(
                value_origin="provider_observation", observation_date_field="period_ending"
            ),
            "fiscal_period": FinancialFieldTemplate(
                value_origin="provider_observation", observation_date_field="period_ending"
            ),
            "currency": FinancialFieldTemplate(
                value_origin="provider_observation", observation_date_field="period_ending"
            ),
            "market_cap": _calculation("currency"),
            "enterprise_value": _calculation("currency"),
            "ev_to_sales": _calculation("multiple"),
            "ev_to_operating_cash_flow": _calculation("multiple"),
            "ev_to_free_cash_flow": _calculation("multiple"),
            "ev_to_ebitda": _calculation("multiple"),
            "net_debt_to_ebitda": _calculation("multiple"),
            "current_ratio": _calculation("multiple"),
            "income_quality": _calculation("multiple"),
            "graham_number": _calculation("currency/share"),
            "graham_net_net": _calculation("currency/share"),
            "tax_burden": _calculation("fraction"),
            "interest_burden": _calculation("fraction"),
            "working_capital": _calculation("currency"),
            "invested_capital": _calculation("currency"),
            "return_on_assets": _calculation("fraction"),
            "operating_return_on_assets": _calculation("fraction"),
            "return_on_tangible_assets": _calculation("fraction"),
            "return_on_equity": _calculation("fraction"),
            "return_on_invested_capital": _calculation("fraction"),
            "return_on_capital_employed": _calculation("fraction"),
            "earnings_yield": _calculation("fraction"),
            "free_cash_flow_yield": _calculation("fraction"),
            "capex_to_operating_cash_flow": _calculation("fraction"),
            "capex_to_depreciation": _calculation("multiple"),
            "capex_to_revenue": _calculation("fraction"),
            "sales_general_and_administrative_to_revenue": _calculation("fraction"),
            "research_and_development_to_revenue": _calculation("fraction"),
            "stock_based_compensation_to_revenue": _calculation("fraction"),
            "intangibles_to_total_assets": _calculation("fraction"),
            "average_receivables": _calculation("currency"),
            "average_payables": _calculation("currency"),
            "average_inventory": _calculation("currency"),
            "days_of_sales_outstanding": _calculation("days"),
            "days_of_payables_outstanding": _calculation("days"),
            "days_of_inventory_outstanding": _calculation("days"),
            "operating_cycle": _calculation("days"),
            "cash_conversion_cycle": _calculation("days"),
            "free_cash_flow_to_equity": _calculation("currency"),
            "free_cash_flow_to_firm": _calculation("currency"),
            "tangible_asset_value": _calculation("currency"),
            "net_current_asset_value": _calculation("currency"),
        },
        runtime_properties=["fields.availability", "fields.period_basis", "retrieved_at",
                            "effective_query", "bounds"],
    )

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    # Preserve the accepted definition where the inherited description is empty.
    market_cap: int | float | None = Field(default=None, description="market_cap")

    __alias_dict__: ClassVar[dict[str, str]] = {
        "period_ending": "date",
        "fiscal_year": "fiscalYear",
        "market_cap": "marketCap",
        "fiscal_period": "period",
        "currency": "reportedCurrency",
        "enterprise_value": "enterpriseValue",
        "ev_to_sales": "evToSales",
        "ev_to_operating_cash_flow": "evToOperatingCashFlow",
        "ev_to_free_cash_flow": "evToFreeCashFlow",
        "ev_to_ebitda": "evToEBITDA",
        "net_debt_to_ebitda": "netDebtToEBITDA",
        "current_ratio": "currentRatio",
        "income_quality": "incomeQuality",
        "graham_number": "grahamNumber",
        "graham_net_net": "grahamNetNet",
        "tax_burden": "taxBurden",
        "interest_burden": "interestBurden",
        "working_capital": "workingCapital",
        "invested_capital": "investedCapital",
        "return_on_assets": "returnOnAssets",
        "operating_return_on_assets": "operatingReturnOnAssets",
        "return_on_tangible_assets": "returnOnTangibleAssets",
        "return_on_equity": "returnOnEquity",
        "return_on_invested_capital": "returnOnInvestedCapital",
        "return_on_capital_employed": "returnOnCapitalEmployed",
        "earnings_yield": "earningsYield",
        "free_cash_flow_yield": "freeCashFlowYield",
        "capex_to_operating_cash_flow": "capexToOperatingCashFlow",
        "capex_to_depreciation": "capexToDepreciation",
        "capex_to_revenue": "capexToRevenue",
        "sales_general_and_administrative_to_revenue": "salesGeneralAndAdministrativeToRevenue",
        "research_and_development_to_revenue": "researchAndDevelopmentToRevenue",
        "stock_based_compensation_to_revenue": "stockBasedCompensationToRevenue",
        "intangibles_to_total_assets": "intangiblesToTotalAssets",
        "average_receivables": "averageReceivables",
        "average_payables": "averagePayables",
        "average_inventory": "averageInventory",
        "days_of_sales_outstanding": "daysOfSalesOutstanding",
        "days_of_payables_outstanding": "daysOfPayablesOutstanding",
        "days_of_inventory_outstanding": "daysOfInventoryOutstanding",
        "operating_cycle": "operatingCycle",
        "cash_conversion_cycle": "cashConversionCycle",
        "free_cash_flow_to_equity": "freeCashFlowToEquity",
        "free_cash_flow_to_firm": "freeCashFlowToFirm",
        "tangible_asset_value": "tangibleAssetValue",
        "net_current_asset_value": "netCurrentAssetValue",
    }

    @model_validator(mode="before")
    @classmethod
    def spelling_alias(cls, value):
        """FMP's stable endpoint spells Developement differently from older payloads."""
        if isinstance(value, dict) and "researchAndDevelopementToRevenue" in value:
            value = dict(value)
            value.setdefault("researchAndDevelopmentToRevenue", value.pop("researchAndDevelopementToRevenue"))
        return value

    enterprise_value: int | float | None = Field(
        default=None, description="Enterprise Value."
    )
    ev_to_sales: float | None = Field(
        default=None, description="Enterprise Value to Sales ratio.", title="EV/Sales"
    )
    ev_to_operating_cash_flow: float | None = Field(
        default=None,
        description="Enterprise Value to Operating Cash Flow ratio.",
        title="EV/Operating Cash Flow",
    )
    ev_to_free_cash_flow: float | None = Field(
        default=None,
        description="Enterprise Value to Free Cash Flow ratio.",
        title="EV/Free Cash Flow",
    )
    ev_to_ebitda: float | None = Field(
        default=None,
        description="Enterprise Value to EBITDA ratio.",
        title="EV/EBITDA",
        alias="evToEBITDA",
    )
    net_debt_to_ebitda: float | None = Field(
        default=None,
        description="Net Debt to EBITDA ratio.",
        title="Net Debt/EBITDA",
        alias="netDebtToEBITDA",
    )
    current_ratio: float | None = Field(default=None, description="Current Ratio.")
    income_quality: float | None = Field(default=None, description="Income Quality.")
    graham_number: float | None = Field(default=None, description="Graham Number.")
    graham_net_net: float | None = Field(default=None, description="Graham Net Net.")
    tax_burden: float | None = Field(default=None, description="Tax Burden.")
    interest_burden: float | None = Field(default=None, description="Interest Burden.")
    working_capital: int | float | None = Field(
        default=None, description="Working Capital."
    )
    invested_capital: int | float | None = Field(
        default=None, description="Invested Capital."
    )
    return_on_assets: float | None = Field(
        default=None,
        description="Return on Assets.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    operating_return_on_assets: float | None = Field(
        default=None,
        description="Operating Return on Assets.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    return_on_tangible_assets: float | None = Field(
        default=None,
        description="Return on Tangible Assets.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    return_on_equity: float | None = Field(
        default=None,
        description="Return on Equity.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    return_on_invested_capital: float | None = Field(
        default=None,
        description="Return on Invested Capital.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    return_on_capital_employed: float | None = Field(
        default=None,
        description="Return on Capital Employed.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    earnings_yield: float | None = Field(
        default=None,
        description="Earnings Yield.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    free_cash_flow_yield: float | None = Field(
        default=None,
        description="Free Cash Flow Yield.",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    capex_to_operating_cash_flow: float | None = Field(
        default=None, description="Capex to Operating Cash Flow."
    )
    capex_to_depreciation: float | None = Field(
        default=None, description="Capex to Depreciation."
    )
    capex_to_revenue: float | None = Field(
        default=None, description="Capex to Revenue."
    )
    sales_general_and_administrative_to_revenue: float | None = Field(
        default=None,
        description="Sales, General and Administrative to Revenue.",
        title="SG&A to Revenue",
    )
    research_and_development_to_revenue: float | None = Field(
        default=None,
        description="Research and Development to Revenue.",
        title="R&D to Revenue",
    )
    stock_based_compensation_to_revenue: float | None = Field(
        default=None, description="Stock Based Compensation to Revenue."
    )
    intangibles_to_total_assets: float | None = Field(
        default=None, description="Intangibles to Total Assets."
    )
    average_receivables: int | float | None = Field(
        default=None, description="Average Receivables."
    )
    average_payables: int | float | None = Field(
        default=None, description="Average Payables."
    )
    average_inventory: int | float | None = Field(
        default=None, description="Average Inventory."
    )
    days_of_sales_outstanding: float | None = Field(
        default=None, description="Days of Sales Outstanding."
    )
    days_of_payables_outstanding: float | None = Field(
        default=None, description="Days of Payables Outstanding."
    )
    days_of_inventory_outstanding: float | None = Field(
        default=None, description="Days of Inventory Outstanding."
    )
    operating_cycle: float | None = Field(default=None, description="Operating Cycle.")
    cash_conversion_cycle: float | None = Field(
        default=None, description="Cash Conversion Cycle."
    )
    free_cash_flow_to_equity: float | None = Field(
        default=None, description="Free Cash Flow to Equity."
    )
    free_cash_flow_to_firm: float | None = Field(
        default=None, description="Free Cash Flow to Firm."
    )
    tangible_asset_value: int | float | None = Field(
        default=None, description="Tangible Asset Value."
    )
    net_current_asset_value: int | float | None = Field(
        default=None, description="Net Current Asset Value."
    )
