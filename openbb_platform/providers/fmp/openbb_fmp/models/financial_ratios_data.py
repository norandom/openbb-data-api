"""Periodic FMP ratio declarations; values retain provider scaling."""

from datetime import date as dateType
from typing import ClassVar

from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from openbb_core.provider.standard_models.financial_ratios import FinancialRatiosData
from pydantic import ConfigDict, Field, model_validator


def _calculation(unit: str) -> FinancialFieldTemplate:
    """Keep provider scaling and unknown valuation conventions explicit."""
    return FinancialFieldTemplate(
        unit=unit, scale=1, value_origin="provider_calculation",
        currency_field="currency" if unit == "currency/share" else None,
        financial_basis={"share_count": None, "debt": None, "cash": None,
                         "lease": None, "minority_interest": None,
                         "forecast_period": None, "market_date": None},
    )


class FMPFinancialRatiosData(FinancialRatiosData):
    """Provider calculations, with no TTM aliases or locally inferred dates."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "symbol": FinancialFieldTemplate(value_origin="provider_observation", observation_date_field="period_ending"),
            "period_ending": FinancialFieldTemplate(value_origin="provider_observation", observation_date_field="period_ending"),
            "fiscal_period": FinancialFieldTemplate(value_origin="provider_observation", observation_date_field="period_ending"),
            "fiscal_year": FinancialFieldTemplate(value_origin="provider_observation", observation_date_field="period_ending"),
            "currency": FinancialFieldTemplate(value_origin="provider_observation", observation_date_field="period_ending"),
            "gross_profit_margin": _calculation("fraction"),
            "ebit_margin": _calculation("fraction"),
            "ebitda_margin": _calculation("fraction"),
            "operating_profit_margin": _calculation("fraction"),
            "pretax_profit_margin": _calculation("fraction"),
            "continuous_operations_profit_margin": _calculation("fraction"),
            "net_profit_margin": _calculation("fraction"),
            "bottom_line_profit_margin": _calculation("fraction"),
            "receivables_turnover": _calculation("multiple"),
            "payables_turnover": _calculation("multiple"),
            "inventory_turnover": _calculation("multiple"),
            "fixed_asset_turnover": _calculation("multiple"),
            "asset_turnover": _calculation("multiple"),
            "current_ratio": _calculation("multiple"),
            "quick_ratio": _calculation("multiple"),
            "solvency_ratio": _calculation("fraction"),
            "cash_ratio": _calculation("multiple"),
            "price_to_earnings": _calculation("multiple"),
            "price_to_earnings_growth": _calculation("multiple"),
            "forward_price_to_earnings_growth": _calculation("multiple"),
            "price_to_book": _calculation("multiple"),
            "price_to_sales": _calculation("multiple"),
            "price_to_free_cash_flow": _calculation("multiple"),
            "price_to_operating_cash_flow": _calculation("multiple"),
            "debt_to_assets": _calculation("fraction"),
            "debt_to_equity": _calculation("multiple"),
            "debt_to_capital": _calculation("fraction"),
            "long_term_debt_to_capital": _calculation("fraction"),
            "financial_leverage_ratio": _calculation("multiple"),
            "working_capital_turnover_ratio": _calculation("multiple"),
            "operating_cash_flow_ratio": _calculation("multiple"),
            "operating_cash_flow_sales_ratio": _calculation("fraction"),
            "free_cash_flow_operating_cash_flow_ratio": _calculation("fraction"),
            "debt_service_coverage_ratio": _calculation("multiple"),
            "interest_coverage_ratio": _calculation("multiple"),
            "short_term_operating_cash_flow_coverage_ratio": _calculation("multiple"),
            "operating_cash_flow_coverage_ratio": _calculation("multiple"),
            "capital_expenditure_coverage_ratio": _calculation("multiple"),
            "dividend_paid_and_capex_coverage_ratio": _calculation("multiple"),
            "dividend_payout_ratio": _calculation("fraction"),
            "dividend_yield": _calculation("fraction"),
            "dividend_per_share": _calculation("currency/share"),
            "revenue_per_share": _calculation("currency/share"),
            "net_income_per_share": _calculation("currency/share"),
            "interest_debt_per_share": _calculation("currency/share"),
            "cash_per_share": _calculation("currency/share"),
            "book_value_per_share": _calculation("currency/share"),
            "tangible_book_value_per_share": _calculation("currency/share"),
            "shareholders_equity_per_share": _calculation("currency/share"),
            "operating_cash_flow_per_share": _calculation("currency/share"),
            "capex_per_share": _calculation("currency/share"),
            "free_cash_flow_per_share": _calculation("currency/share"),
            "net_income_per_ebt": _calculation("fraction"),
            "ebt_per_ebit": _calculation("fraction"),
            "price_to_fair_value": _calculation("multiple"),
            "debt_to_market_cap": _calculation("fraction"),
            "effective_tax_rate": _calculation("fraction"),
            "enterprise_value_multiple": _calculation("multiple"),
            "dividend_yield_percentage": _calculation("percent"),
            "price_to_earnings_diluted": _calculation("multiple"),
            "price_to_earnings_diluted_growth": _calculation("multiple"),
        },
        runtime_properties=["fields.availability", "fields.period_basis", "retrieved_at",
                            "effective_query", "bounds"],
    )

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    __alias_dict__: ClassVar[dict] = {
        "currency": "reportedCurrency",
        "period_ending": "date",
        "fiscal_period": "period",
        "price_to_earnings": "priceToEarningsRatio",
        "price_to_earnings_growth": "priceToEarningsGrowthRatio",
        "forward_price_to_earnings_growth": "forwardPriceToEarningsGrowthRatio",
        "price_to_book": "priceToBookRatio",
        "price_to_sales": "priceToSalesRatio",
        "price_to_free_cash_flow": "priceToFreeCashFlowRatio",
        "price_to_operating_cash_flow": "priceToOperatingCashFlowRatio",
        "debt_to_assets": "debtToAssetsRatio",
        "debt_to_equity": "debtToEquityRatio",
        "debt_to_capital": "debtToCapitalRatio",
        "debt_to_market_cap": "debtToMarketCap",
        "long_term_debt_to_capital": "longTermDebtToCapitalRatio",
        "net_income_per_ebt": "netIncomePerEBT",
        "ebt_per_ebit": "ebtPerEbit",
        "price_to_fair_value": "priceToFairValue",
        "effective_tax_rate": "effectiveTaxRate",
        "enterprise_value_multiple": "enterpriseValueMultiple",
        "gross_profit_margin": "grossProfitMargin",
        "ebit_margin": "ebitMargin",
        "ebitda_margin": "ebitdaMargin",
        "operating_profit_margin": "operatingProfitMargin",
        "pretax_profit_margin": "pretaxProfitMargin",
        "continuous_operations_profit_margin": "continuousOperationsProfitMargin",
        "net_profit_margin": "netProfitMargin",
        "bottom_line_profit_margin": "bottomLineProfitMargin",
        "receivables_turnover": "receivablesTurnover",
        "payables_turnover": "payablesTurnover",
        "inventory_turnover": "inventoryTurnover",
        "fixed_asset_turnover": "fixedAssetTurnover",
        "asset_turnover": "assetTurnover",
        "current_ratio": "currentRatio",
        "quick_ratio": "quickRatio",
        "solvency_ratio": "solvencyRatio",
        "cash_ratio": "cashRatio",
        "financial_leverage_ratio": "financialLeverageRatio",
        "working_capital_turnover_ratio": "workingCapitalTurnoverRatio",
        "operating_cash_flow_ratio": "operatingCashFlowRatio",
        "operating_cash_flow_sales_ratio": "operatingCashFlowSalesRatio",
        "free_cash_flow_operating_cash_flow_ratio": "freeCashFlowOperatingCashFlowRatio",
        "debt_service_coverage_ratio": "debtServiceCoverageRatio",
        "interest_coverage_ratio": "interestCoverageRatio",
        "short_term_operating_cash_flow_coverage_ratio": "shortTermOperatingCashFlowCoverageRatio",
        "operating_cash_flow_coverage_ratio": "operatingCashFlowCoverageRatio",
        "capital_expenditure_coverage_ratio": "capitalExpenditureCoverageRatio",
        "dividend_paid_and_capex_coverage_ratio": "dividendPaidAndCapexCoverageRatio",
        "dividend_payout_ratio": "dividendPayoutRatio",
        "dividend_yield": "dividendYield",
        "revenue_per_share": "revenuePerShare",
        "net_income_per_share": "netIncomePerShare",
        "interest_debt_per_share": "interestDebtPerShare",
        "cash_per_share": "cashPerShare",
        "book_value_per_share": "bookValuePerShare",
        "tangible_book_value_per_share": "tangibleBookValuePerShare",
        "shareholders_equity_per_share": "shareholdersEquityPerShare",
        "operating_cash_flow_per_share": "operatingCashFlowPerShare",
        "capex_per_share": "capexPerShare",
        "free_cash_flow_per_share": "freeCashFlowPerShare",
        "dividend_per_share": "dividendPerShare",
        "fiscal_year": "fiscalYear",
        "dividend_yield_percentage": "dividendYieldPercentage",
        "price_to_earnings_diluted": "priceToEarningsDilutedRatio",
        "price_to_earnings_diluted_growth": "priceToEarningsDilutedGrowthRatio",
    }

    currency: str | None = Field(
        default=None, description='Currency in which the company reports financials.',
    )
    gross_profit_margin: float | None = Field(
        default=None, description='Gross profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    ebit_margin: float | None = Field(
        default=None, description='Earnings before interest and taxes (EBIT) margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    ebitda_margin: float | None = Field(
        default=None, description='Earnings before interest, taxes, depreciation, and amortization (EBITDA) margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    operating_profit_margin: float | None = Field(
        default=None, description='Operating profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    pretax_profit_margin: float | None = Field(
        default=None, description='Pretax profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    continuous_operations_profit_margin: float | None = Field(
        default=None, description='Continuous operations profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    net_profit_margin: float | None = Field(
        default=None, description='Net profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    bottom_line_profit_margin: float | None = Field(
        default=None, description='Bottom line profit margin. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    receivables_turnover: float | None = Field(
        default=None, description='Receivables turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    payables_turnover: float | None = Field(
        default=None, description='Payables turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    inventory_turnover: float | None = Field(
        default=None, description='Inventory turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    fixed_asset_turnover: float | None = Field(
        default=None, description='Fixed asset turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    asset_turnover: float | None = Field(
        default=None, description='Asset turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    current_ratio: float | None = Field(
        default=None, description='Current ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    quick_ratio: float | None = Field(
        default=None, description='Quick ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    solvency_ratio: float | None = Field(
        default=None, description='Solvency ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    cash_ratio: float | None = Field(
        default=None, description='Cash ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_earnings: float | None = Field(
        default=None, description='Price to earnings (P/E) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_earnings_growth: float | None = Field(
        default=None, description='Price to earnings growth (PEG) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    forward_price_to_earnings_growth: float | None = Field(
        default=None, description='Forward price to earnings growth (PEG) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_book: float | None = Field(
        default=None, description='Price to book (P/B) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_sales: float | None = Field(
        default=None, description='Price to sales (P/S) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_free_cash_flow: float | None = Field(
        default=None, description='Price to free cash flow (P/FCF) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_operating_cash_flow: float | None = Field(
        default=None, description='Price to operating cash flow (P/OCF) ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    debt_to_assets: float | None = Field(
        default=None, description='Debt to assets ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    debt_to_equity: float | None = Field(
        default=None, description='Debt to equity ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    debt_to_capital: float | None = Field(
        default=None, description='Debt to capital ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    long_term_debt_to_capital: float | None = Field(
        default=None, description='Long-term debt to capital ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    financial_leverage_ratio: float | None = Field(
        default=None, description='Financial leverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    working_capital_turnover_ratio: float | None = Field(
        default=None, description='Working capital turnover ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    operating_cash_flow_ratio: float | None = Field(
        default=None, description='Operating cash flow ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    operating_cash_flow_sales_ratio: float | None = Field(
        default=None, description='Operating cash flow to sales ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    free_cash_flow_operating_cash_flow_ratio: float | None = Field(
        default=None, description='Free cash flow to operating cash flow ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    debt_service_coverage_ratio: float | None = Field(
        default=None, description='Debt service coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    interest_coverage_ratio: float | None = Field(
        default=None, description='Interest coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    short_term_operating_cash_flow_coverage_ratio: float | None = Field(
        default=None, description='Short-term operating cash flow coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    operating_cash_flow_coverage_ratio: float | None = Field(
        default=None, description='Operating cash flow coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    capital_expenditure_coverage_ratio: float | None = Field(
        default=None, description='Capital expenditure coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    dividend_paid_and_capex_coverage_ratio: float | None = Field(
        default=None, description='Dividend paid and capital expenditure coverage ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    dividend_payout_ratio: float | None = Field(
        default=None, description='Dividend payout ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    dividend_yield: float | None = Field(
        default=None, description='Dividend yield. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    dividend_per_share: float | None = Field(
        default=None, description='Dividend per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    revenue_per_share: float | None = Field(
        default=None, description='Revenue per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    net_income_per_share: float | None = Field(
        default=None, description='Net income per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    interest_debt_per_share: float | None = Field(
        default=None, description='Interest-bearing debt per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    cash_per_share: float | None = Field(
        default=None, description='Cash per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    book_value_per_share: float | None = Field(
        default=None, description='Book value per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    tangible_book_value_per_share: float | None = Field(
        default=None, description='Tangible book value per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    shareholders_equity_per_share: float | None = Field(
        default=None, description="Shareholders' equity per share. Provider calculation; exact accounting and averaging conventions unavailable.",
    )
    operating_cash_flow_per_share: float | None = Field(
        default=None, description='Operating cash flow per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    capex_per_share: float | None = Field(
        default=None, description='Capital expenditure per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    free_cash_flow_per_share: float | None = Field(
        default=None, description='Free cash flow per share. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    net_income_per_ebt: float | None = Field(
        default=None, description='Net income per earnings before tax (EBT). Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    ebt_per_ebit: float | None = Field(
        default=None, description='Earnings before tax (EBT) per earnings before interest and tax (EBIT). Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    price_to_fair_value: float | None = Field(
        default=None, description='Price to fair value ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    debt_to_market_cap: float | None = Field(
        default=None, description='Debt to market capitalization ratio. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    effective_tax_rate: float | None = Field(
        default=None, description='Effective tax rate. Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    enterprise_value_multiple: float | None = Field(
        default=None, description='Enterprise value multiple (EV/EBITDA). Provider calculation; exact accounting and averaging conventions unavailable.',
    )
    dividend_yield_percentage: float | None = Field(default=None, description='Provider dividend yield in percentage points. Provider calculation; exact accounting and averaging conventions unavailable.')
    price_to_earnings_diluted: float | None = Field(default=None, description='Provider diluted P/E multiple. Provider calculation; exact accounting and averaging conventions unavailable.')
    price_to_earnings_diluted_growth: float | None = Field(default=None, description='Provider diluted PEG multiple; growth convention unavailable. Provider calculation; exact accounting and averaging conventions unavailable.')
    period_ending: dateType = Field(description="Provider fiscal period ending date.")

    @model_validator(mode="before")
    @classmethod
    def legacy_year(cls, values):
        """Accept the retained fiscal-year spelling without deriving a year."""
        if isinstance(values, dict) and "calendarYear" in values and "fiscalYear" not in values:
            values = {**values, "fiscalYear": values["calendarYear"]}
        return values
