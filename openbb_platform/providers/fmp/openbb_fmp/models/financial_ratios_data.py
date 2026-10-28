"""Periodic FMP ratio declarations; values retain provider scaling."""

from datetime import date as dateType
from typing import ClassVar

from openbb_core.provider.standard_models.financial_ratios import FinancialRatiosData
from pydantic import ConfigDict, Field, model_validator


class FMPFinancialRatiosData(FinancialRatiosData):
    """Provider calculations, with no TTM aliases or locally inferred dates."""

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
        default=None, description='Gross profit margin.',
    )
    ebit_margin: float | None = Field(
        default=None, description='Earnings before interest and taxes (EBIT) margin.',
    )
    ebitda_margin: float | None = Field(
        default=None, description='Earnings before interest, taxes, depreciation, and amortization (EBITDA) margin.',
    )
    operating_profit_margin: float | None = Field(
        default=None, description='Operating profit margin.',
    )
    pretax_profit_margin: float | None = Field(
        default=None, description='Pretax profit margin.',
    )
    continuous_operations_profit_margin: float | None = Field(
        default=None, description='Continuous operations profit margin.',
    )
    net_profit_margin: float | None = Field(
        default=None, description='Net profit margin.',
    )
    bottom_line_profit_margin: float | None = Field(
        default=None, description='Bottom line profit margin.',
    )
    receivables_turnover: float | None = Field(
        default=None, description='Receivables turnover ratio.',
    )
    payables_turnover: float | None = Field(
        default=None, description='Payables turnover ratio.',
    )
    inventory_turnover: float | None = Field(
        default=None, description='Inventory turnover ratio.',
    )
    fixed_asset_turnover: float | None = Field(
        default=None, description='Fixed asset turnover ratio.',
    )
    asset_turnover: float | None = Field(
        default=None, description='Asset turnover ratio.',
    )
    current_ratio: float | None = Field(
        default=None, description='Current ratio.',
    )
    quick_ratio: float | None = Field(
        default=None, description='Quick ratio.',
    )
    solvency_ratio: float | None = Field(
        default=None, description='Solvency ratio.',
    )
    cash_ratio: float | None = Field(
        default=None, description='Cash ratio.',
    )
    price_to_earnings: float | None = Field(
        default=None, description='Price to earnings (P/E) ratio.',
    )
    price_to_earnings_growth: float | None = Field(
        default=None, description='Price to earnings growth (PEG) ratio.',
    )
    forward_price_to_earnings_growth: float | None = Field(
        default=None, description='Forward price to earnings growth (PEG) ratio.',
    )
    price_to_book: float | None = Field(
        default=None, description='Price to book (P/B) ratio.',
    )
    price_to_sales: float | None = Field(
        default=None, description='Price to sales (P/S) ratio.',
    )
    price_to_free_cash_flow: float | None = Field(
        default=None, description='Price to free cash flow (P/FCF) ratio.',
    )
    price_to_operating_cash_flow: float | None = Field(
        default=None, description='Price to operating cash flow (P/OCF) ratio.',
    )
    debt_to_assets: float | None = Field(
        default=None, description='Debt to assets ratio.',
    )
    debt_to_equity: float | None = Field(
        default=None, description='Debt to equity ratio.',
    )
    debt_to_capital: float | None = Field(
        default=None, description='Debt to capital ratio.',
    )
    long_term_debt_to_capital: float | None = Field(
        default=None, description='Long-term debt to capital ratio.',
    )
    financial_leverage_ratio: float | None = Field(
        default=None, description='Financial leverage ratio.',
    )
    working_capital_turnover_ratio: float | None = Field(
        default=None, description='Working capital turnover ratio.',
    )
    operating_cash_flow_ratio: float | None = Field(
        default=None, description='Operating cash flow ratio.',
    )
    operating_cash_flow_sales_ratio: float | None = Field(
        default=None, description='Operating cash flow to sales ratio.',
    )
    free_cash_flow_operating_cash_flow_ratio: float | None = Field(
        default=None, description='Free cash flow to operating cash flow ratio.',
    )
    debt_service_coverage_ratio: float | None = Field(
        default=None, description='Debt service coverage ratio.',
    )
    interest_coverage_ratio: float | None = Field(
        default=None, description='Interest coverage ratio.',
    )
    short_term_operating_cash_flow_coverage_ratio: float | None = Field(
        default=None, description='Short-term operating cash flow coverage ratio.',
    )
    operating_cash_flow_coverage_ratio: float | None = Field(
        default=None, description='Operating cash flow coverage ratio.',
    )
    capital_expenditure_coverage_ratio: float | None = Field(
        default=None, description='Capital expenditure coverage ratio.',
    )
    dividend_paid_and_capex_coverage_ratio: float | None = Field(
        default=None, description='Dividend paid and capital expenditure coverage ratio.',
    )
    dividend_payout_ratio: float | None = Field(
        default=None, description='Dividend payout ratio.',
    )
    dividend_yield: float | None = Field(
        default=None, description='Dividend yield.',
    )
    dividend_per_share: float | None = Field(
        default=None, description='Dividend per share.',
    )
    revenue_per_share: float | None = Field(
        default=None, description='Revenue per share.',
    )
    net_income_per_share: float | None = Field(
        default=None, description='Net income per share.',
    )
    interest_debt_per_share: float | None = Field(
        default=None, description='Interest-bearing debt per share.',
    )
    cash_per_share: float | None = Field(
        default=None, description='Cash per share.',
    )
    book_value_per_share: float | None = Field(
        default=None, description='Book value per share.',
    )
    tangible_book_value_per_share: float | None = Field(
        default=None, description='Tangible book value per share.',
    )
    shareholders_equity_per_share: float | None = Field(
        default=None, description="Shareholders' equity per share.",
    )
    operating_cash_flow_per_share: float | None = Field(
        default=None, description='Operating cash flow per share.',
    )
    capex_per_share: float | None = Field(
        default=None, description='Capital expenditure per share.',
    )
    free_cash_flow_per_share: float | None = Field(
        default=None, description='Free cash flow per share.',
    )
    net_income_per_ebt: float | None = Field(
        default=None, description='Net income per earnings before tax (EBT).',
    )
    ebt_per_ebit: float | None = Field(
        default=None, description='Earnings before tax (EBT) per earnings before interest and tax (EBIT).',
    )
    price_to_fair_value: float | None = Field(
        default=None, description='Price to fair value ratio.',
    )
    debt_to_market_cap: float | None = Field(
        default=None, description='Debt to market capitalization ratio.',
    )
    effective_tax_rate: float | None = Field(
        default=None, description='Effective tax rate.',
    )
    enterprise_value_multiple: float | None = Field(
        default=None, description='Enterprise value multiple (EV/EBITDA).',
    )
    dividend_yield_percentage: float | None = Field(default=None, description="Provider dividend yield in percentage points.")
    price_to_earnings_diluted: float | None = Field(default=None, description="Provider diluted P/E multiple.")
    price_to_earnings_diluted_growth: float | None = Field(default=None, description="Provider diluted PEG multiple; growth convention unavailable.")
    period_ending: dateType = Field(description="Provider fiscal period ending date.")

    @model_validator(mode="before")
    @classmethod
    def legacy_year(cls, values):
        """Accept the retained fiscal-year spelling without deriving a year."""
        if isinstance(values, dict) and "calendarYear" in values and "fiscalYear" not in values:
            values = {**values, "fiscalYear": values["calendarYear"]}
        return values
