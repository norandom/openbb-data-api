"""Retained FMP cash-flow field meanings and stable/legacy aliases."""
from datetime import (
    date as dateType,
    datetime,
)
from typing import ClassVar

from openbb_core.provider.standard_models.cash_flow import CashFlowStatementData
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from pydantic import Field, model_validator


def _cash_template(amount=False, calculated=False, stock=False, opening=False) -> FinancialFieldTemplate:
    """Declare cash stocks and flows without deriving provider calculation formulas."""
    return FinancialFieldTemplate(
        unit="currency" if amount else None,
        scale=1 if amount else None,
        currency_field="reported_currency" if amount else None,
        period_basis="instant" if stock else None,
        value_origin="provider_calculation" if calculated else "provider_observation",
        observation_date_field=None if opening else "period_ending",
        publication_date_field="filing_date",
        financial_basis={"cash": None} if amount else {},
    )


class FMPCashFlowStatementData(CashFlowStatementData):
    """FMP Cash Flow Statement Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "period_ending": _cash_template(),
            "fiscal_period": _cash_template(),
            "fiscal_year": _cash_template(),
            "filing_date": _cash_template(),
            "accepted_date": _cash_template(),
            "cik": _cash_template(),
            "symbol": _cash_template(),
            "reported_currency": _cash_template(),
            "net_income": _cash_template(amount=True),
            "depreciation_and_amortization": _cash_template(amount=True),
            "deferred_income_tax": _cash_template(amount=True),
            "stock_based_compensation": _cash_template(amount=True),
            "change_in_working_capital": _cash_template(amount=True),
            "change_in_account_receivables": _cash_template(amount=True),
            "change_in_inventory": _cash_template(amount=True),
            "change_in_account_payable": _cash_template(amount=True),
            "change_in_other_working_capital": _cash_template(amount=True),
            "change_in_other_non_cash_items": _cash_template(amount=True),
            "net_cash_from_operating_activities": _cash_template(amount=True),
            "purchase_of_property_plant_and_equipment": _cash_template(amount=True),
            "acquisitions": _cash_template(amount=True),
            "purchase_of_investment_securities": _cash_template(amount=True),
            "sale_and_maturity_of_investments": _cash_template(amount=True),
            "other_investing_activities": _cash_template(amount=True),
            "net_cash_from_investing_activities": _cash_template(amount=True),
            "repayment_of_debt": _cash_template(amount=True),
            "issuance_of_common_equity": _cash_template(amount=True),
            "repurchase_of_common_equity": _cash_template(amount=True),
            "net_common_equity_issuance": _cash_template(amount=True),
            "net_preferred_equity_issuance": _cash_template(amount=True),
            "net_equity_issuance": _cash_template(amount=True),
            "short_term_net_debt_issuance": _cash_template(amount=True),
            "long_term_net_debt_issuance": _cash_template(amount=True),
            "net_debt_issuance": _cash_template(amount=True),
            "common_dividends_paid": _cash_template(amount=True),
            "preferred_dividends_paid": _cash_template(amount=True),
            "net_dividends_paid": _cash_template(amount=True),
            "payment_of_dividends": _cash_template(amount=True),
            "other_financing_activities": _cash_template(amount=True),
            "net_cash_from_financing_activities": _cash_template(amount=True),
            "effect_of_exchange_rate_changes_on_cash": _cash_template(amount=True),
            "net_change_in_cash_and_equivalents": _cash_template(amount=True),
            "cash_at_beginning_of_period": _cash_template(amount=True, stock=True, opening=True),
            "cash_at_end_of_period": _cash_template(amount=True, stock=True),
            "operating_cash_flow": _cash_template(amount=True, calculated=True),
            "capital_expenditure": _cash_template(amount=True),
            "income_taxes_paid": _cash_template(amount=True),
            "interest_paid": _cash_template(amount=True),
            "free_cash_flow": _cash_template(amount=True, calculated=True),
        },
        runtime_properties=["fields.availability", "fields.period_basis", "retrieved_at",
                            "effective_query", "bounds"],
    )

    __alias_dict__: ClassVar[dict] = {
        "period_ending": "date",
        "fiscal_period": "period",
        "fiscal_year": "calendarYear",
        "filing_date": "fillingDate",
        "accepted_date": "acceptedDate",
        "reported_currency": "reportedCurrency",
        "net_income": "netIncome",
        "short_term_net_debt_issuance": "shortTermNetDebtIssuance",
        "long_term_net_debt_issuance": "longTermNetDebtIssuance",
        "net_debt_issuance": "netDebtIssuance",
        "common_dividends_paid": "commonDividendsPaid",
        "preferred_dividends_paid": "preferredDividendsPaid",
        "net_dividends_paid": "netDividendsPaid",
        "income_taxes_paid": "incomeTaxesPaid",
        "interest_paid": "interestPaid",
        "depreciation_and_amortization": "depreciationAndAmortization",
        "deferred_income_tax": "deferredIncomeTax",
        "stock_based_compensation": "stockBasedCompensation",
        "change_in_working_capital": "changeInWorkingCapital",
        "change_in_account_receivables": "accountsReceivables",
        "change_in_inventory": "inventory",
        "change_in_account_payable": "accountsPayables",
        "change_in_other_working_capital": "otherWorkingCapital",
        "change_in_other_non_cash_items": "otherNonCashItems",
        "net_cash_from_operating_activities": "netCashProvidedByOperatingActivities",
        "purchase_of_property_plant_and_equipment": "investmentsInPropertyPlantAndEquipment",
        "acquisitions": "acquisitionsNet",
        "purchase_of_investment_securities": "purchasesOfInvestments",
        "sale_and_maturity_of_investments": "salesMaturitiesOfInvestments",
        "other_investing_activities": "otherInvestingActivities",
        "net_cash_from_investing_activities": "netCashProvidedByInvestingActivities",
        "repayment_of_debt": "debtRepayment",
        "issuance_of_common_equity": "commonStockIssuance",
        "repurchase_of_common_equity": "commonStockRepurchased",
        "net_common_equity_issuance": "netCommonStockIssuance",
        "net_preferred_equity_issuance": "netPreferredStockIssuance",
        "net_equity_issuance": "netStockIssuance",
        "payment_of_dividends": "dividendsPaid",
        "other_financing_activities": "otherFinancingActivities",
        "net_cash_from_financing_activities": "netCashProvidedByFinancingActivities",
        "effect_of_exchange_rate_changes_on_cash": "effectOfForexChangesOnCash",
        "net_change_in_cash_and_equivalents": "netChangeInCash",
        "cash_at_beginning_of_period": "cashAtBeginningOfPeriod",
        "cash_at_end_of_period": "cashAtEndOfPeriod",
        "operating_cash_flow": "operatingCashFlow",
        "capital_expenditure": "capitalExpenditure",
        "free_cash_flow": "freeCashFlow",
    }

    @model_validator(mode="before")
    @classmethod
    def statement_aliases(cls, values):
        """Preserve provider dates across current and legacy key spellings."""
        if isinstance(values, dict):
            values = values.copy()
            for legacy, current in (("calendarYear", "fiscalYear"), ("fillingDate", "filingDate")):
                if current in values:
                    values[legacy] = values[current]
        return values

    fiscal_year: int | None = Field(
        default=None,
        description="The fiscal year of the fiscal period.",
    )
    filing_date: dateType | None = Field(
        default=None,
        description="The date of the filing.",
    )
    accepted_date: datetime | None = Field(
        default=None, description="The date the filing was accepted."
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
        description="The currency in which the cash flow statement was reported.",
    )
    net_income: int | None = Field(
        default=None,
        description="Net income.",
    )
    depreciation_and_amortization: int | None = Field(
        default=None,
        description="Depreciation and amortization.",
    )
    deferred_income_tax: int | None = Field(
        default=None,
        description="Deferred income tax.",
    )
    stock_based_compensation: int | None = Field(
        default=None,
        description="Stock-based compensation.",
    )
    change_in_working_capital: int | None = Field(
        default=None,
        description="Change in working capital.",
    )
    change_in_account_receivables: int | None = Field(
        default=None,
        description="Change in account receivables.",
    )
    change_in_inventory: int | None = Field(
        default=None,
        description="Change in inventory.",
    )
    change_in_account_payable: int | None = Field(
        default=None,
        description="Change in account payable.",
    )
    change_in_other_working_capital: int | None = Field(
        default=None,
        description="Change in other working capital.",
    )
    change_in_other_non_cash_items: int | None = Field(
        default=None,
        description="Change in other non-cash items.",
    )
    net_cash_from_operating_activities: int | None = Field(
        default=None,
        description="Net cash from operating activities.",
    )
    purchase_of_property_plant_and_equipment: int | None = Field(
        default=None,
        description="Purchase of property, plant and equipment.",
    )
    acquisitions: int | None = Field(
        default=None,
        description="Acquisitions.",
    )
    purchase_of_investment_securities: int | None = Field(
        default=None,
        description="Purchase of investment securities.",
    )
    sale_and_maturity_of_investments: int | None = Field(
        default=None,
        description="Sale and maturity of investments.",
    )
    other_investing_activities: int | None = Field(
        default=None,
        description="Other investing activities.",
    )
    net_cash_from_investing_activities: int | None = Field(
        default=None,
        description="Net cash from investing activities.",
    )
    repayment_of_debt: int | None = Field(
        default=None,
        description="Repayment of debt.",
    )
    issuance_of_common_equity: int | None = Field(
        default=None,
        description="Issuance of common equity.",
    )
    repurchase_of_common_equity: int | None = Field(
        default=None,
        description="Repurchase of common equity.",
    )
    net_common_equity_issuance: int | None = Field(
        default=None,
        description="Net common equity issuance.",
    )
    net_preferred_equity_issuance: int | None = Field(
        default=None,
        description="Net preferred equity issuance.",
    )
    net_equity_issuance: int | None = Field(
        default=None,
        description="Net equity issuance.",
    )
    short_term_net_debt_issuance: int | None = Field(
        default=None,
        description="Short term net debt issuance.",
    )
    long_term_net_debt_issuance: int | None = Field(
        default=None,
        description="Long term net debt issuance.",
    )
    net_debt_issuance: int | None = Field(
        default=None,
        description="Net debt issuance.",
    )
    common_dividends_paid: int | None = Field(
        default=None,
        description="Payment of common dividends.",
    )
    preferred_dividends_paid: int | None = Field(
        default=None,
        description="Payment of preferred dividends.",
    )
    net_dividends_paid: int | None = Field(
        default=None,
        description="Net dividends paid.",
    )
    payment_of_dividends: int | None = Field(
        default=None,
        description="Provider-reported aggregate dividends paid, preserving its sign convention.",
    )
    other_financing_activities: int | None = Field(
        default=None,
        description="Other financing activities.",
    )
    net_cash_from_financing_activities: int | None = Field(
        default=None,
        description="Net cash from financing activities.",
    )
    effect_of_exchange_rate_changes_on_cash: int | None = Field(
        default=None,
        description="Effect of exchange rate changes on cash.",
    )
    net_change_in_cash_and_equivalents: int | None = Field(
        default=None,
        description="Net change in cash and equivalents.",
    )
    cash_at_beginning_of_period: int | None = Field(
        default=None,
        description="Cash at beginning of period.",
    )
    cash_at_end_of_period: int | None = Field(
        default=None,
        description="Cash at end of period.",
    )
    operating_cash_flow: int | None = Field(
        default=None,
        description="Operating cash flow.",
    )
    capital_expenditure: int | None = Field(
        default=None,
        description="Capital expenditure.",
    )
    income_taxes_paid: int | None = Field(
        default=None,
        description="Income taxes paid.",
    )
    interest_paid: int | None = Field(
        default=None,
        description="Interest paid.",
    )
    free_cash_flow: int | None = Field(
        default=None,
        description="Provider-reported free cash flow; calculation definition unavailable.",
    )
