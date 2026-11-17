"""Retained income growth declarations preserve signed provider ratios."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# 10a662a63ff4781993815f083b5a074a0a5858eea64087b2d11a49afb68cf9d2.
import re
from datetime import date
from math import isfinite
from typing import ClassVar

from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from openbb_core.provider.standard_models.income_statement_growth import (
    IncomeStatementGrowthData,
)
from openbb_core.provider.utils.descriptions import DATA_DESCRIPTIONS
from pydantic import ConfigDict, Field, field_validator


def _growth_template(name):
    """Flow comparisons disclose unknown denominator and duration conventions."""
    growth = name.startswith("growth_")
    return FinancialFieldTemplate(
        unit="ratio" if growth else None,
        scale=1 if growth else None,
        value_origin="provider_calculation" if growth else "provider_observation",
        observation_date_field="period_ending",
        period_basis="flow growth; discrete versus year-to-date duration, source denominator periods and restatement unknown",
        financial_basis={"market_date": None},
    )


class FMPIncomeStatementGrowthData(IncomeStatementGrowthData):
    """FMP Income Statement Growth Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation]
    model_config = ConfigDict(extra="ignore")

    __alias_dict__ = {
        "period_ending": "date",
        "fiscal_year": "calendarYear",
        "fiscal_period": "period",
        "growth_ebit": "growthEBIT",
        "growth_ebitda": "growthEBITDA",
        "growth_basic_earings_per_share": "growthEPS",
        "growth_gross_profit_margin": "growthGrossProfitRatio",
        "growth_consolidated_net_income": "growthNetIncome",
        "growth_diluted_earnings_per_share": "growthEPSDiluted",
        "growth_weighted_average_basic_shares_outstanding": "growthWeightedAverageShsOut",
        "growth_weighted_average_diluted_shares_outstanding": "growthWeightedAverageShsOutDil",
        "growth_research_and_development_expense": "growthResearchAndDevelopmentExpenses",
        "growth_general_and_admin_expense": "growthGeneralAndAdministrativeExpenses",
        "growth_selling_and_marketing_expense": "growthSellingAndMarketingExpenses",
    }

    symbol: str = Field(description=DATA_DESCRIPTIONS.get("symbol", ""))
    reported_currency: str | None = Field(
        description="The currency in which the financial data is reported.",
        default=None,
    )
    growth_revenue: float | None = Field(
        default=None,
        description="Growth rate of total revenue.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_cost_of_revenue: float | None = Field(
        default=None,
        description="Growth rate of cost of goods sold.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_gross_profit: float | None = Field(
        default=None,
        description="Growth rate of gross profit.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_gross_profit_margin: float | None = Field(
        default=None,
        description="Growth rate of gross profit as a percentage of revenue.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_general_and_admin_expense: float | None = Field(
        default=None,
        description="Growth rate of general and administrative expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_research_and_development_expense: float | None = Field(
        default=None,
        description="Growth rate of expenses on research and development.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_selling_and_marketing_expense: float | None = Field(
        default=None,
        description="Growth rate of expenses on selling and marketing activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_expenses: float | None = Field(
        default=None,
        description="Growth rate of other operating expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_operating_expenses: float | None = Field(
        default=None,
        description="Growth rate of total operating expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_cost_and_expenses: float | None = Field(
        default=None,
        description="Growth rate of total costs and expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_depreciation_and_amortization: float | None = Field(
        default=None,
        description="Growth rate of depreciation and amortization expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_interest_income: float | None = Field(
        default=None,
        description="Growth rate of interest income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_interest_expense: float | None = Field(
        default=None,
        description="Growth rate of interest expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_interest_income: float | None = Field(
        default=None,
        description="Growth rate of net interest income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_ebit: float | None = Field(
        default=None,
        description="Growth rate of Earnings Before Interest and Taxes (EBIT).",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_ebitda: float | None = Field(
        default=None,
        description="Growth rate of Earnings Before Interest, Taxes, Depreciation, and Amortization.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_operating_income: float | None = Field(
        default=None,
        description="Growth rate of operating income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_non_operating_income_excluding_interest: float | None = Field(
        default=None,
        description="Growth rate of non-operating income excluding interest.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_other_income_expenses_net: float | None = Field(
        default=None,
        description="Growth rate of net total other income and expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_adjustments_to_net_income: float | None = Field(
        default=None,
        description="Growth rate of other adjustments to net income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_income_deductions: float | None = Field(
        default=None,
        description="Growth rate of net income deductions.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_income_before_tax: float | None = Field(
        default=None,
        description="Growth rate of income before taxes.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_income_tax_expense: float | None = Field(
        default=None,
        description="Growth rate of income tax expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_income_from_continuing_operations: float | None = Field(
        default=None,
        description="Growth rate of net income from continuing operations.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_consolidated_net_income: float | None = Field(
        default=None,
        description="Growth rate of net income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_basic_earings_per_share: float | None = Field(
        default=None,
        description="Growth rate of Earnings Per Share (EPS).",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_diluted_earnings_per_share: float | None = Field(
        default=None,
        description="Growth rate of diluted Earnings Per Share (EPS).",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_weighted_average_basic_shares_outstanding: float | None = Field(
        default=None,
        description="Growth rate of weighted average shares outstanding.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_weighted_average_diluted_shares_outstanding: float | None = Field(
        default=None,
        description="Growth rate of diluted weighted average shares outstanding.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )

    @field_validator("period_ending", mode="before")
    @classmethod
    def calendar_period_end(cls, value):
        """Reject epoch and timestamp guesses for fiscal calendar ends."""
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Invalid fiscal period end")
        return date.fromisoformat(value)

    @field_validator("*", mode="wrap")
    @classmethod
    def safe_facts(cls, value, handler):
        """Contain inherited conversions and reject nonfinite source ratios."""
        try:
            result = handler(value)
        except (TypeError, ValueError, OverflowError):
            pass
        else:
            if not isinstance(result, float) or isfinite(result):
                return result
        raise ValueError("Invalid financial result field")


FMPIncomeStatementGrowthData.financial_data_annotation = FinancialDataAnnotation(
    fields={
        name: _growth_template(name)
        for name in FMPIncomeStatementGrowthData.model_fields
    },
    runtime_properties=[
        "fields.availability",
        "retrieved_at",
        "effective_query",
        "bounds",
    ],
)
