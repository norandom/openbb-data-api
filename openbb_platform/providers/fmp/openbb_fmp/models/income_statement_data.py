"""Income field definitions and static reporting semantics."""

from datetime import date as dateType
from datetime import datetime
from typing import ClassVar

from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from openbb_core.provider.standard_models.income_statement import IncomeStatementData
from pydantic import Field, model_validator


def _observation(unit: str | None = None) -> FinancialFieldTemplate:
    """Retain each reported currency and fiscal date as a row-level reference."""
    return FinancialFieldTemplate(
        unit=unit, scale=1 if unit else None,
        currency_field="reported_currency" if unit in {"currency", "currency/share"} else None,
        value_origin="provider_observation", observation_date_field="period_ending",
        publication_date_field="filing_date",
    )


class FMPIncomeStatementData(IncomeStatementData):
    """FMP Income Statement Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "period_ending": _observation(),
            "fiscal_period": _observation(),
            "fiscal_year": _observation(),
            "filing_date": _observation(),
            "accepted_date": _observation(),
            "cik": _observation(),
            "symbol": _observation(),
            "reported_currency": _observation(),
            "revenue": _observation("currency"),
            "cost_of_revenue": _observation("currency"),
            "gross_profit": _observation("currency"),
            "general_and_admin_expense": _observation("currency"),
            "research_and_development_expense": _observation("currency"),
            "selling_and_marketing_expense": _observation("currency"),
            "selling_general_and_admin_expense": _observation("currency"),
            "other_expenses": _observation("currency"),
            "total_operating_expenses": _observation("currency"),
            "cost_and_expenses": _observation("currency"),
            "interest_income": _observation("currency"),
            "total_interest_expense": _observation("currency"),
            "net_interest_income": _observation("currency"),
            "depreciation_and_amortization": _observation("currency"),
            "ebit": _observation("currency"),
            "ebitda": _observation("currency"),
            "total_operating_income": _observation("currency"),
            "non_operating_income_excluding_interest": _observation("currency"),
            "net_income_from_continuing_operations": _observation("currency"),
            "net_income_from_discontinued_operations": _observation("currency"),
            "total_other_income_expenses": _observation("currency"),
            "total_pre_tax_income": _observation("currency"),
            "income_tax_expense": _observation("currency"),
            "other_adjustments_to_net_income": _observation("currency"),
            "net_income_deductions": _observation("currency"),
            "consolidated_net_income": _observation("currency"),
            "bottom_line_net_income": _observation("currency"),
            "basic_earnings_per_share": _observation("currency/share"),
            "diluted_earnings_per_share": _observation("currency/share"),
            "weighted_average_basic_shares_outstanding": _observation("shares"),
            "weighted_average_diluted_shares_outstanding": _observation("shares"),
        },
        runtime_properties=["fields.period_basis", "fields.availability", "retrieved_at",
                            "effective_query", "bounds"],
    )

    __alias_dict__: ClassVar[dict] = {
        "period_ending": "date",
        "fiscal_period": "period",
        "fiscal_year": "calendarYear",
        "filing_date": "fillingDate",
        "accepted_date": "acceptedDate",
        "reported_currency": "reportedCurrency",
        "revenue": "revenue",
        "cost_of_revenue": "costOfRevenue",
        "gross_profit": "grossProfit",
        "general_and_admin_expense": "generalAndAdministrativeExpenses",
        "research_and_development_expense": "researchAndDevelopmentExpenses",
        "selling_and_marketing_expense": "sellingAndMarketingExpenses",
        "selling_general_and_admin_expense": "sellingGeneralAndAdministrativeExpenses",
        "other_expenses": "otherExpenses",
        "total_operating_expenses": "operatingExpenses",
        "cost_and_expenses": "costAndExpenses",
        "interest_income": "interestIncome",
        "total_interest_expense": "interestExpense",
        "depreciation_and_amortization": "depreciationAndAmortization",
        "ebitda": "ebitda",
        "total_operating_income": "operatingIncome",
        "total_other_income_expenses": "totalOtherIncomeExpensesNet",
        "total_pre_tax_income": "incomeBeforeTax",
        "income_tax_expense": "incomeTaxExpense",
        "consolidated_net_income": "netIncome",
        "basic_earnings_per_share": "eps",
        "diluted_earnings_per_share": "epsDiluted",
        "weighted_average_basic_shares_outstanding": "weightedAverageShsOut",
        "weighted_average_diluted_shares_outstanding": "weightedAverageShsOutDil",
    }

    @model_validator(mode="before")
    @classmethod
    def statement_aliases(cls, values):
        """Accept stable and legacy spellings without changing fiscal observations."""
        if isinstance(values, dict):
            values = values.copy()
            for legacy, current in (("calendarYear", "fiscalYear"), ("fillingDate", "filingDate")):
                if current in values:
                    values[legacy] = values[current]
        return values

    filing_date: dateType | None = Field(
        default=None,
        description="The date when the filing was made.",
    )
    accepted_date: datetime | None = Field(
        default=None,
        description="The date and time when the filing was accepted.",
    )
    cik: str | None = Field(
        default=None,
        description="The Central Index Key (CIK) assigned by the SEC, if applicable.",
    )
    symbol: str | None = Field(
        default=None,
        description="The stock ticker symbol.",
    )
    reported_currency: str | None = Field(
        default=None,
        description="The currency in which the balance sheet was reported.",
    )
    revenue: int | None = Field(
        default=None,
        description="Total revenue.",
    )
    cost_of_revenue: int | None = Field(
        default=None,
        description="Cost of revenue.",
    )
    gross_profit: int | None = Field(
        default=None,
        description="Gross profit.",
    )
    general_and_admin_expense: int | None = Field(
        default=None,
        description="General and administrative expenses.",
    )
    research_and_development_expense: int | None = Field(
        default=None,
        description="Research and development expenses.",
    )
    selling_and_marketing_expense: int | None = Field(
        default=None,
        description="Selling and marketing expenses.",
    )
    selling_general_and_admin_expense: int | None = Field(
        default=None,
        description="Selling, general and administrative expenses.",
    )
    other_expenses: int | None = Field(
        default=None,
        description="Other expenses.",
    )
    total_operating_expenses: int | None = Field(
        default=None,
        description="Total operating expenses.",
    )
    cost_and_expenses: int | None = Field(
        default=None,
        description="Cost and expenses.",
    )
    interest_income: int | None = Field(
        default=None,
        description="Interest income.",
    )
    total_interest_expense: int | None = Field(
        default=None,
        description="Total interest expenses.",
    )
    net_interest_income: int | None = Field(
        default=None,
        description="Net interest income.",
    )
    depreciation_and_amortization: int | None = Field(
        default=None,
        description="Depreciation and amortization.",
    )
    ebit: int | None = Field(
        default=None,
        description="Earnings before interest and taxes (EBIT).",
        title="EBIT",
    )
    ebitda: int | None = Field(
        default=None,
        description="EBITDA.",
        title="EBITDA",
    )
    total_operating_income: int | None = Field(
        default=None,
        description="Total operating income.",
    )
    non_operating_income_excluding_interest: int | None = Field(
        default=None,
        description="Non-operating income excluding interest.",
    )
    net_income_from_continuing_operations: int | None = Field(
        default=None,
        description="Net income from continuing operations.",
    )
    net_income_from_discontinued_operations: int | None = Field(
        default=None,
        description="Net income from discontinued operations.",
    )
    total_other_income_expenses: int | None = Field(
        default=None,
        description="Total other income and expenses.",
    )
    total_pre_tax_income: int | None = Field(
        default=None,
        description="Total pre-tax income.",
    )
    income_tax_expense: int | None = Field(
        default=None,
        description="Income tax expense.",
    )
    other_adjustments_to_net_income: int | None = Field(
        default=None,
        description="Other adjustments to net income.",
    )
    net_income_deductions: int | None = Field(
        default=None,
        description="Net income deductions.",
    )
    consolidated_net_income: int | None = Field(
        default=None,
        description="Consolidated net income.",
    )
    bottom_line_net_income: int | None = Field(
        default=None,
        description="Bottom line net income.",
    )
    basic_earnings_per_share: float | None = Field(
        default=None,
        description="Basic earnings per share.",
    )
    diluted_earnings_per_share: float | None = Field(
        default=None,
        description="Diluted earnings per share.",
    )
    weighted_average_basic_shares_outstanding: int | None = Field(
        default=None,
        description="Weighted average basic shares outstanding.",
    )
    weighted_average_diluted_shares_outstanding: int | None = Field(
        default=None,
        description="Weighted average diluted shares outstanding.",
    )
