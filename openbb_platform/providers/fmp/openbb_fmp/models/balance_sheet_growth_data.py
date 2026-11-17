"""Retained balance growth declarations preserve signed provider ratios."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# fb9f08cfa2721f97dedee402abff4bdef968d8c6e1d55baff9dc0d5f663c75a0.
import re
from datetime import date
from math import isfinite
from typing import ClassVar

from openbb_core.provider.standard_models.balance_sheet_growth import (
    BalanceSheetGrowthData,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from pydantic import ConfigDict, Field, field_validator


def _growth_template(name):
    """Stock comparisons disclose unknown denominator and restatement basis."""
    growth = name.startswith("growth_")
    return FinancialFieldTemplate(
        unit="ratio" if growth else None,
        scale=1 if growth else None,
        value_origin="provider_calculation" if growth else "provider_observation",
        observation_date_field="period_ending",
        period_basis="stock comparison; source denominator periods and restatement unknown",
        financial_basis={"market_date": None},
    )


class FMPBalanceSheetGrowthData(BalanceSheetGrowthData):
    """FMP Balance Sheet Growth Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation]
    model_config = ConfigDict(extra="ignore")

    __alias_dict__ = {
        "period_ending": "date",
        "fiscal_year": "calendarYear",
        "fiscal_period": "period",
        "reported_currency": "reportedCurrency",
        "growth_other_total_shareholders_equity": "growthOthertotalStockholdersEquity",
        "growth_total_shareholders_equity": "growthTotalStockholdersEquity",
        "growth_total_liabilities_and_shareholders_equity": "growthTotalLiabilitiesAndStockholdersEquity",
        "growth_accumulated_other_comprehensive_income": "growthAccumulatedOtherComprehensiveIncomeLoss",
        "growth_prepaid_expenses": "growthPrepaids",
    }

    symbol: str = Field(
        description="Symbol representing the entity requested in the data.",
    )
    reported_currency: str | None = Field(
        default=None,
        description="The currency in which the financial data is reported.",
    )
    growth_cash_and_cash_equivalents: float | None = Field(
        default=None,
        description="Growth rate of cash and cash equivalents.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_short_term_investments: float | None = Field(
        default=None,
        description="Growth rate of short-term investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_cash_and_short_term_investments: float | None = Field(
        default=None,
        description="Growth rate of cash and short-term investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_accounts_receivables: float | None = Field(
        default=None,
        description="Growth rate of accounts receivable.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_receivables: float | None = Field(
        default=None,
        description="Growth rate of other receivables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_receivables: float | None = Field(
        default=None,
        description="Growth rate of net receivables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_inventory: float | None = Field(
        default=None,
        description="Growth rate of inventory.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_current_assets: float | None = Field(
        default=None,
        description="Growth rate of other current assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_current_assets: float | None = Field(
        default=None,
        description="Growth rate of total current assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_property_plant_equipment_net: float | None = Field(
        description="Growth rate of net property, plant, and equipment.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_goodwill: float | None = Field(
        description="Growth rate of goodwill.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_intangible_assets: float | None = Field(
        description="Growth rate of intangible assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_goodwill_and_intangible_assets: float | None = Field(
        description="Growth rate of goodwill and intangible assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_long_term_investments: float | None = Field(
        default=None,
        description="Growth rate of long-term investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_tax_assets: float | None = Field(
        default=None,
        description="Growth rate of tax assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_non_current_assets: float | None = Field(
        default=None,
        description="Growth rate of other non-current assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_non_current_assets: float | None = Field(
        default=None,
        description="Growth rate of total non-current assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_assets: float | None = Field(
        default=None,
        description="Growth rate of other assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_assets: float | None = Field(
        default=None,
        description="Growth rate of total assets.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_account_payables: float | None = Field(
        default=None,
        description="Growth rate of accounts payable.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_payables: float | None = Field(
        default=None,
        description="Growth rate of other payables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_payables: float | None = Field(
        default=None,
        description="Growth rate of total payables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_accrued_expenses: float | None = Field(
        default=None,
        description="Growth rate of accrued expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_prepaid_expenses: float | None = Field(
        default=None,
        description="Growth rate of prepaid expenses.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_capital_lease_obligations_current: float | None = Field(
        default=None,
        description="Growth rate of current capital lease obligations.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_short_term_debt: float | None = Field(
        default=None,
        description="Growth rate of short-term debt.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_tax_payables: float | None = Field(
        default=None,
        description="Growth rate of tax payables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_deferred_revenue: float | None = Field(
        default=None,
        description="Growth rate of deferred revenue.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_current_liabilities: float | None = Field(
        default=None,
        description="Growth rate of other current liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_current_liabilities: float | None = Field(
        default=None,
        description="Growth rate of total current liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_deferred_revenue_non_current: float | None = Field(
        default=None,
        description="Growth rate of non-current deferred revenue.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_long_term_debt: float | None = Field(
        default=None,
        description="Growth rate of long-term debt.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_deferred_tax_liabilities_non_current: float | None = Field(
        default=None,
        description="Growth rate of non-current deferred tax liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_non_current_liabilities: float | None = Field(
        default=None,
        description="Growth rate of other non-current liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_non_current_liabilities: float | None = Field(
        default=None,
        description="Growth rate of total non-current liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_liabilities: float | None = Field(
        description="Growth rate of other liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_liabilities: float | None = Field(
        description="Growth rate of total liabilities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_retained_earnings: float | None = Field(
        description="Growth rate of retained earnings.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_accumulated_other_comprehensive_income: float | None = Field(
        description="Growth rate of accumulated other comprehensive income/loss.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_minority_interest: float | None = Field(
        default=None,
        description="Growth rate of minority interest.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_additional_paid_in_capital: float | None = Field(
        default=None,
        description="Growth rate of additional paid-in capital.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_total_shareholders_equity: float | None = Field(
        default=None,
        description="Growth rate of other total stockholders' equity.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_shareholders_equity: float | None = Field(
        default=None,
        description="Growth rate of total stockholders' equity.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_common_stock: float | None = Field(
        description="Growth rate of common stock.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_preferred_stock: float | None = Field(
        description="Growth rate of preferred stock.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_treasury_stock: float | None = Field(
        default=None,
        description="Growth rate of treasury stock.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_equity: float | None = Field(
        default=None,
        description="Growth rate of total equity.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_liabilities_and_shareholders_equity: float | None = Field(
        default=None,
        description="Growth rate of total liabilities and stockholders' equity.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_investments: float | None = Field(
        default=None,
        description="Growth rate of total investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_total_debt: float | None = Field(
        default=None,
        description="Growth rate of total debt.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_debt: float | None = Field(
        default=None,
        description="Growth rate of net debt.",
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


FMPBalanceSheetGrowthData.financial_data_annotation = FinancialDataAnnotation(
    fields={
        name: _growth_template(name) for name in FMPBalanceSheetGrowthData.model_fields
    },
    runtime_properties=[
        "fields.availability",
        "retrieved_at",
        "effective_query",
        "bounds",
    ],
)
