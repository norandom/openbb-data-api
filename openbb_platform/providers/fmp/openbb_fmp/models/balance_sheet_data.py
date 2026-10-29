"""Retained FMP balance-sheet fields; amounts remain in reported currency units."""

from datetime import (
    date as dateType,
    datetime,
)
from typing import ClassVar

from openbb_core.provider.standard_models.balance_sheet import BalanceSheetData
from openbb_core.provider.standard_models.financial_annotations import (
    FinancialDataAnnotation,
    FinancialFieldTemplate,
)
from pydantic import Field, model_validator


def _balance_template(amount=False, basis=None) -> FinancialFieldTemplate:
    """Declare reported stocks without asserting undocumented valuation bridges."""
    bases = {
        "debt": "Provider-reported; lease inclusion and netting conventions unknown.",
        "cash": "Provider-reported cash category; unrestricted cash basis unknown.",
        "lease": "Provider-reported capital lease category; accounting scope unknown.",
        "minority_interest": "Provider-reported non-controlling interest category.",
    }
    return FinancialFieldTemplate(
        unit="currency" if amount else None,
        scale=1 if amount else None,
        currency_field="reported_currency" if amount else None,
        period_basis="instant" if amount else None,
        value_origin="provider_observation",
        observation_date_field="period_ending",
        publication_date_field="filing_date",
        financial_basis={basis: bases[basis]} if basis is not None else {},
    )


class FMPBalanceSheetData(BalanceSheetData):
    """FMP Balance Sheet Data."""

    financial_data_annotation: ClassVar[FinancialDataAnnotation] = FinancialDataAnnotation(
        fields={
            "period_ending": _balance_template(),
            "fiscal_period": _balance_template(),
            "fiscal_year": _balance_template(),
            "filing_date": _balance_template(),
            "accepted_date": _balance_template(),
            "cik": _balance_template(),
            "symbol": _balance_template(),
            "reported_currency": _balance_template(),
            "cash_and_cash_equivalents": _balance_template(amount=True, basis="cash"),
            "short_term_investments": _balance_template(amount=True),
            "cash_and_short_term_investments": _balance_template(amount=True, basis="cash"),
            "accounts_receivables": _balance_template(amount=True),
            "other_receivables": _balance_template(amount=True),
            "net_receivables": _balance_template(amount=True),
            "inventory": _balance_template(amount=True),
            "other_current_assets": _balance_template(amount=True),
            "total_current_assets": _balance_template(amount=True),
            "plant_property_equipment_net": _balance_template(amount=True),
            "goodwill": _balance_template(amount=True),
            "intangible_assets": _balance_template(amount=True),
            "goodwill_and_intangible_assets": _balance_template(amount=True),
            "long_term_investments": _balance_template(amount=True),
            "tax_assets": _balance_template(amount=True),
            "other_non_current_assets": _balance_template(amount=True),
            "non_current_assets": _balance_template(amount=True),
            "other_assets": _balance_template(amount=True),
            "total_assets": _balance_template(amount=True),
            "accounts_payable": _balance_template(amount=True),
            "prepaid_expenses": _balance_template(amount=True),
            "accrued_expenses": _balance_template(amount=True),
            "short_term_debt": _balance_template(amount=True, basis="debt"),
            "tax_payables": _balance_template(amount=True),
            "current_deferred_revenue": _balance_template(amount=True),
            "other_current_liabilities": _balance_template(amount=True),
            "other_payables": _balance_template(amount=True),
            "total_current_liabilities": _balance_template(amount=True),
            "total_payables": _balance_template(amount=True),
            "long_term_debt": _balance_template(amount=True, basis="debt"),
            "deferred_revenue_non_current": _balance_template(amount=True),
            "deferred_tax_liabilities_non_current": _balance_template(amount=True),
            "other_non_current_liabilities": _balance_template(amount=True),
            "total_non_current_liabilities": _balance_template(amount=True),
            "capital_lease_obligations_current": _balance_template(amount=True, basis="lease"),
            "capital_lease_obligations_non_current": _balance_template(amount=True, basis="lease"),
            "capital_lease_obligations": _balance_template(amount=True, basis="lease"),
            "other_liabilities": _balance_template(amount=True),
            "total_liabilities": _balance_template(amount=True),
            "preferred_stock": _balance_template(amount=True),
            "common_stock": _balance_template(amount=True),
            "treasury_stock": _balance_template(amount=True),
            "retained_earnings": _balance_template(amount=True),
            "additional_paid_in_capital": _balance_template(amount=True),
            "accumulated_other_comprehensive_income": _balance_template(amount=True),
            "other_shareholders_equity": _balance_template(amount=True),
            "other_total_shareholders_equity": _balance_template(amount=True),
            "total_common_equity": _balance_template(amount=True),
            "total_equity_non_controlling_interests": _balance_template(amount=True, basis="minority_interest"),
            "total_liabilities_and_shareholders_equity": _balance_template(amount=True),
            "minority_interest": _balance_template(amount=True, basis="minority_interest"),
            "total_liabilities_and_total_equity": _balance_template(amount=True),
            "total_investments": _balance_template(amount=True),
            "total_debt": _balance_template(amount=True, basis="debt"),
            "net_debt": _balance_template(amount=True, basis="debt"),
        },
        runtime_properties=["fields.availability", "retrieved_at",
                            "effective_query", "bounds"],
    )

    __alias_dict__: ClassVar[dict] = {
        "period_ending": "date",
        "fiscal_period": "period",
        "fiscal_year": "calendarYear",
        "filing_date": "fillingDate",
        "accepted_date": "acceptedDate",
        "reported_currency": "reportedCurrency",
        "cash_and_cash_equivalents": "cashAndCashEquivalents",
        "short_term_investments": "shortTermInvestments",
        "cash_and_short_term_investments": "cashAndShortTermInvestments",
        "net_receivables": "netReceivables",
        "inventory": "inventories",
        "other_current_assets": "otherCurrentAssets",
        "total_current_assets": "totalCurrentAssets",
        "plant_property_equipment_net": "propertyPlantEquipmentNet",
        "goodwill": "goodwill",
        "prepaid_expenses": "prepaids",
        "intangible_assets": "intangibleAssets",
        "goodwill_and_intangible_assets": "goodwillAndIntangibleAssets",
        "long_term_investments": "longTermInvestments",
        "tax_assets": "taxAssets",
        "other_non_current_assets": "otherNonCurrentAssets",
        "non_current_assets": "totalNonCurrentAssets",
        "other_assets": "otherAssets",
        "total_assets": "totalAssets",
        "accounts_payable": "accountPayables",
        "short_term_debt": "shortTermDebt",
        "tax_payables": "taxPayables",
        "current_deferred_revenue": "deferredRevenue",
        "other_current_liabilities": "otherCurrentLiabilities",
        "total_current_liabilities": "totalCurrentLiabilities",
        "long_term_debt": "longTermDebt",
        "deferred_revenue_non_current": "deferredRevenueNonCurrent",
        "deferred_tax_liabilities_non_current": "deferredTaxLiabilitiesNonCurrent",
        "other_non_current_liabilities": "otherNonCurrentLiabilities",
        "total_non_current_liabilities": "totalNonCurrentLiabilities",
        "other_liabilities": "otherLiabilities",
        "capital_lease_obligations": "capitalLeaseObligations",
        "total_liabilities": "totalLiabilities",
        "preferred_stock": "preferredStock",
        "common_stock": "commonStock",
        "retained_earnings": "retainedEarnings",
        "accumulated_other_comprehensive_income": "accumulatedOtherComprehensiveIncomeLoss",
        "other_shareholders_equity": "otherStockholdersEquity",
        "other_total_shareholders_equity": "otherTotalStockholdersEquity",
        "total_common_equity": "totalStockholdersEquity",
        "total_equity_non_controlling_interests": "totalEquity",
        "total_liabilities_and_shareholders_equity": "totalLiabilitiesAndStockholdersEquity",
        "minority_interest": "minorityInterest",
        "total_liabilities_and_total_equity": "totalLiabilitiesAndTotalEquity",
        "total_investments": "totalInvestments",
        "total_debt": "totalDebt",
        "net_debt": "netDebt",
    }

    @model_validator(mode="before")
    @classmethod
    def statement_aliases(cls, values):
        """Accept current and legacy fiscal/filing names without inventing dates."""
        if isinstance(values, dict):
            values = values.copy()
            for legacy, current in (("calendarYear", "fiscalYear"), ("fillingDate", "filingDate")):
                if current in values:
                    values[legacy] = values[current]
        return values

    filing_date: dateType | None = Field(
        default=None, description="The date when the filing was made."
    )
    accepted_date: datetime | None = Field(
        default=None, description="The date and time when the filing was accepted."
    )
    cik: str | None = Field(
        default=None, description="The Central Index Key (CIK) assigned by the SEC, if applicable."
    )
    symbol: str | None = Field(
        default=None, description="The stock ticker symbol."
    )
    reported_currency: str | None = Field(
        default=None, description="The currency in which the balance sheet was reported."
    )
    cash_and_cash_equivalents: int | None = Field(
        default=None, description="Cash and cash equivalents."
    )
    short_term_investments: int | None = Field(
        default=None, description="Short term investments."
    )
    cash_and_short_term_investments: int | None = Field(
        default=None, description="Cash and short term investments."
    )
    accounts_receivables: int | None = Field(
        default=None, description="Accounts receivables."
    )
    other_receivables: int | None = Field(
        default=None, description="Other receivables."
    )
    net_receivables: int | None = Field(
        default=None, description="Net receivables."
    )
    inventory: int | None = Field(
        default=None, description="Inventory."
    )
    other_current_assets: int | None = Field(
        default=None, description="Other current assets."
    )
    total_current_assets: int | None = Field(
        default=None, description="Total current assets."
    )
    plant_property_equipment_net: int | None = Field(
        default=None, description="Plant property equipment net."
    )
    goodwill: int | None = Field(
        default=None, description="Goodwill."
    )
    intangible_assets: int | None = Field(
        default=None, description="Intangible assets."
    )
    goodwill_and_intangible_assets: int | None = Field(
        default=None, description="Goodwill and intangible assets."
    )
    long_term_investments: int | None = Field(
        default=None, description="Long term investments."
    )
    tax_assets: int | None = Field(
        default=None, description="Tax assets."
    )
    other_non_current_assets: int | None = Field(
        default=None, description="Other non current assets."
    )
    non_current_assets: int | None = Field(
        default=None, description="Total non current assets."
    )
    other_assets: int | None = Field(
        default=None, description="Other assets."
    )
    total_assets: int | None = Field(
        default=None, description="Total assets."
    )
    accounts_payable: int | None = Field(
        default=None, description="Accounts payable."
    )
    prepaid_expenses: int | None = Field(
        default=None, description="Prepaid expenses."
    )
    accrued_expenses: int | None = Field(
        default=None, description="Accrued expenses."
    )
    short_term_debt: int | None = Field(
        default=None, description="Short term debt."
    )
    tax_payables: int | None = Field(
        default=None, description="Tax payables."
    )
    current_deferred_revenue: int | None = Field(
        default=None, description="Current deferred revenue."
    )
    other_current_liabilities: int | None = Field(
        default=None, description="Other current liabilities."
    )
    other_payables: int | None = Field(
        default=None, description="Other payables."
    )
    total_current_liabilities: int | None = Field(
        default=None, description="Total current liabilities."
    )
    total_payables: int | None = Field(
        default=None, description="Total payables."
    )
    long_term_debt: int | None = Field(
        default=None, description="Long term debt."
    )
    deferred_revenue_non_current: int | None = Field(
        default=None, description="Non current deferred revenue."
    )
    deferred_tax_liabilities_non_current: int | None = Field(
        default=None, description="Deferred tax liabilities non current."
    )
    other_non_current_liabilities: int | None = Field(
        default=None, description="Other non current liabilities."
    )
    total_non_current_liabilities: int | None = Field(
        default=None, description="Total non current liabilities."
    )

    capital_lease_obligations_current: int | None = Field(
        default=None, description="Current capital lease obligations."
    )
    capital_lease_obligations_non_current: int | None = Field(
        default=None, description="Non current capital lease obligations."
    )
    capital_lease_obligations: int | None = Field(
        default=None, description="Capital lease obligations."
    )
    other_liabilities: int | None = Field(
        default=None, description="Other liabilities."
    )
    total_liabilities: int | None = Field(
        default=None, description="Total liabilities."
    )
    preferred_stock: int | None = Field(
        default=None, description="Preferred stock."
    )
    common_stock: int | None = Field(
        default=None, description="Common stock."
    )
    treasury_stock: int | None = Field(
        default=None, description="Treasury stock."
    )
    retained_earnings: int | None = Field(
        default=None, description="Retained earnings."
    )
    additional_paid_in_capital: int | None = Field(
        default=None, description="Additional paid in capital."
    )
    accumulated_other_comprehensive_income: int | None = Field(
        default=None, description="Accumulated other comprehensive income (loss)."
    )
    other_shareholders_equity: int | None = Field(
        default=None, description="Other shareholders equity."
    )
    other_total_shareholders_equity: int | None = Field(
        default=None, description="Other total shareholders equity."
    )
    total_common_equity: int | None = Field(
        default=None, description="Total common equity."
    )
    total_equity_non_controlling_interests: int | None = Field(
        default=None, description="Total equity non controlling interests."
    )
    total_liabilities_and_shareholders_equity: int | None = Field(
        default=None, description="Total liabilities and shareholders equity."
    )
    minority_interest: int | None = Field(
        default=None, description="Minority interest."
    )
    total_liabilities_and_total_equity: int | None = Field(
        default=None, description="Total liabilities and total equity."
    )
    total_investments: int | None = Field(
        default=None, description="Total investments."
    )
    total_debt: int | None = Field(
        default=None, description="Total debt."
    )
    net_debt: int | None = Field(
        default=None, description="Net debt."
    )
