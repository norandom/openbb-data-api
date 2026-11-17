"""Retained cash flow growth declarations preserve signed provider ratios."""

# Copyright (c) 2021-2025 OpenBB Inc.
# Adapted from OpenBB FMP 1.6.1, AGPL-3.0-only; retained source SHA-256:
# b1fd6e773908f80e0c8b3400dfa679127a75ac074bba635ebb988d1c05c9ae03.
import re
from datetime import date
from math import isfinite
from typing import ClassVar

from openbb_core.provider.standard_models.cash_flow_growth import (
    CashFlowStatementGrowthData,
)
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from pydantic import ConfigDict, Field, field_validator, model_validator


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


class FMPCashFlowStatementGrowthData(CashFlowStatementGrowthData):  # noqa: D101
    financial_data_annotation: ClassVar[FinancialDataAnnotation]
    model_config = ConfigDict(extra="ignore")

    __alias_dict__ = {
        "period_ending": "date",
        "fiscal_year": "calendarYear",
        "fiscal_period": "period",
        "reported_currency": "reportedCurrency",
        "growth_acquisitions": "growthAcquisitionsNet",
        "growth_sale_and_maturity_of_investments": "growthSalesMaturitiesOfInvestments",
        "growth_net_cash_from_operating_activities": "growthNetCashProvidedByOperatingActivities",
        "growth_other_investing_activities": "growthOtherInvestingActivities",
        "growth_net_cash_from_investing_activities": "growthNetCashUsedForInvestingActivities",
        "growth_other_financing_activities": "growthOtherFinancingActivities",
        "growth_purchase_of_investment_securities": "growthPurchasesOfInvestments",
        "growth_account_receivables": "growthAccountsReceivables",
        "growth_account_payable": "growthAccountsPayables",
        "growth_purchase_of_property_plant_and_equipment": "growthInvestmentsInPropertyPlantAndEquipment",
        "growth_repayment_of_debt": "growthDebtRepayment",
        "growth_net_change_in_cash_and_equivalents": "growthNetChangeInCash",
        "growth_effect_of_exchange_rate_changes_on_cash": "growthEffectOfForexChangesOnCash",
        "growth_net_cash_from_financing_activities": "growthNetCashUsedProvidedByFinancingActivities",
        "growth_net_equity_issuance": "growthNetStockIssuance",
        "growth_common_equity_issuance": "growthCommonStockIssued",
        "growth_common_equity_repurchased": "growthCommonStockRepurchased",
    }

    symbol: str = Field(
        description="Symbol representing the entity requested in the data.",
    )
    reported_currency: str | None = Field(
        default=None,
        description="The currency in which the financial data is reported.",
    )
    growth_net_income: float | None = Field(
        default=None,
        description="Growth rate of net income.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_depreciation_and_amortization: float | None = Field(
        default=None,
        description="Growth rate of depreciation and amortization.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_deferred_income_tax: float | None = Field(
        default=None,
        description="Growth rate of deferred income tax.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_stock_based_compensation: float | None = Field(
        default=None,
        description="Growth rate of stock-based compensation.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_change_in_working_capital: float | None = Field(
        default=None,
        description="Growth rate of change in working capital.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_account_receivables: float | None = Field(
        default=None,
        description="Growth rate of accounts receivables.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_inventory: float | None = Field(
        default=None,
        description="Growth rate of inventory.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_account_payable: float | None = Field(
        default=None,
        description="Growth rate of account payable.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_working_capital: float | None = Field(
        default=None,
        description="Growth rate of other working capital.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_non_cash_items: float | None = Field(
        default=None,
        description="Growth rate of other non-cash items.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_cash_from_operating_activities: float | None = Field(
        default=None,
        description="Growth rate of net cash provided by operating activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_purchase_of_property_plant_and_equipment: float | None = Field(
        default=None,
        description="Growth rate of investments in property, plant, and equipment.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_acquisitions: float | None = Field(
        default=None,
        description="Growth rate of net acquisitions.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_purchase_of_investment_securities: float | None = Field(
        default=None,
        description="Growth rate of purchases of investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_sale_and_maturity_of_investments: float | None = Field(
        default=None,
        description="Growth rate of sales maturities of investments.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_investing_activities: float | None = Field(
        default=None,
        description="Growth rate of other investing activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_cash_from_investing_activities: float | None = Field(
        default=None,
        description="Growth rate of net cash used for investing activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_short_term_net_debt_issuance: float | None = Field(
        default=None,
        description="Growth rate of short term net debt issuance.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_long_term_net_debt_issuance: float | None = Field(
        default=None,
        description="Growth rate of long term net debt issuance.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_debt_issuance: float | None = Field(
        default=None,
        description="Growth rate of net debt issuance.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_repayment_of_debt: float | None = Field(
        default=None,
        description="Growth rate of debt repayment.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_common_equity_issuance: float | None = Field(
        default=None,
        description="Growth rate of common equity issued.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_common_equity_repurchased: float | None = Field(
        default=None,
        description="Growth rate of common equity repurchased.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_equity_issuance: float | None = Field(
        default=None,
        description="Growth rate of net equity issuance.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_dividends_paid: float | None = Field(
        default=None,
        description="Growth rate of dividends paid.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_preferred_dividends_paid: float | None = Field(
        default=None,
        description="Growth rate of preferred dividends paid.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_other_financing_activities: float | None = Field(
        default=None,
        description="Growth rate of other financing activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_cash_from_financing_activities: float | None = Field(
        default=None,
        description="Growth rate of net cash used/provided by financing activities.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_effect_of_exchange_rate_changes_on_cash: float | None = Field(
        default=None,
        description="Growth rate of the effect of foreign exchange changes on cash.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_net_change_in_cash_and_equivalents: float | None = Field(
        default=None,
        description="Growth rate of net change in cash.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_cash_at_beginning_of_period: float | None = Field(
        default=None,
        description="Growth rate of cash at the beginning of the period.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_cash_at_end_of_period: float | None = Field(
        default=None,
        description="Growth rate of cash at the end of the period.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_operating_cash_flow: float | None = Field(
        default=None,
        description="Growth rate of operating cash flow.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_capital_expenditure: float | None = Field(
        default=None,
        description="Growth rate of capital expenditure.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_income_taxes_paid: float | None = Field(
        default=None,
        description="Growth rate of income taxes paid.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_interest_paid: float | None = Field(
        default=None,
        description="Growth rate of interest paid.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )
    growth_free_cash_flow: float | None = Field(
        default=None,
        description="Growth rate of free cash flow.",
        json_schema_extra={"x-unit_measurement": "ratio"},
    )

    _source_spelling_pairs: ClassVar[dict[str, list[str]]] = {
        "growth_net_cash_from_operating_activities": [
            "growthNetCashProvidedByOperatingActivities",
            "growthNetCashProvidedByOperatingActivites",
        ],
        "growth_other_investing_activities": [
            "growthOtherInvestingActivities",
            "growthOtherInvestingActivites",
        ],
        "growth_net_cash_from_investing_activities": [
            "growthNetCashUsedForInvestingActivities",
            "growthNetCashUsedForInvestingActivites",
        ],
        "growth_other_financing_activities": [
            "growthOtherFinancingActivities",
            "growthOtherFinancingActivites",
        ],
    }

    @model_validator(mode="before")
    @classmethod
    def source_spellings(cls, value):
        """Reconcile only evidenced source spellings; conflicting facts fail closed."""
        if not isinstance(value, dict):
            return value
        result = value.copy()
        for name, aliases in cls._source_spelling_pairs.items():
            field = cls.model_fields[name]
            keys = {name, field.validation_alias, *aliases}
            present = [key for key in keys if key in result]
            if not present:
                continue
            fact = result[present[0]]
            if any(result[key] != fact for key in present[1:]):
                raise ValueError("Conflicting financial result aliases")
            result[aliases[0]] = fact
        return result

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


FMPCashFlowStatementGrowthData.financial_data_annotation = FinancialDataAnnotation(
    fields={
        name: _growth_template(name)
        for name in FMPCashFlowStatementGrowthData.model_fields
    },
    runtime_properties=[
        "fields.availability",
        "retrieved_at",
        "effective_query",
        "bounds",
    ],
)
