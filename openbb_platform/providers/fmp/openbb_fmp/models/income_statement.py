"""FMP Income Statement Model."""

# pylint: disable=unused-argument

from datetime import (
    date as dateType,
)
from datetime import (
    datetime,
)
from typing import Any, ClassVar
from urllib.parse import urlencode

from openbb_core.provider.abstract.annotated_result import AnnotatedResult
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialResultMetadata,
    FinancialSource,
)
from openbb_core.provider.standard_models.income_statement import (
    IncomeStatementData,
    IncomeStatementQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.financial_validation import validate_financial_result
from pydantic import Field, field_validator, model_validator

from openbb_fmp.utils.definitions import FinancialStatementPeriods
from openbb_fmp.utils.helpers import FMPAcquisition


class FMPIncomeStatementQueryParams(IncomeStatementQueryParams):
    """FMP Income Statement Query.

    Source: https://financialmodelingprep.com/developer/docs/#Income-Statement
    """

    @field_validator("symbol", mode="after")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Trim surrounding whitespace without changing ticker punctuation."""
        return value.strip()

    @field_validator("limit", mode="after")
    @classmethod
    def bounded_limit(cls, value):
        """Preserve zero while bounding the baseline request."""
        if value is not None and value > 1000:
            raise ValueError("Limit must not exceed 1000.")
        return value

    period: FinancialStatementPeriods = Field(
        default="annual",
        description=QUERY_DESCRIPTIONS.get("period", ""),
    )


class FMPIncomeStatementData(IncomeStatementData):
    """FMP Income Statement Data."""

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


class FMPIncomeStatementFetcher(
    Fetcher[
        FMPIncomeStatementQueryParams,
        list[FMPIncomeStatementData],
    ]
):
    """FMP Income Statement Fetcher."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> FMPIncomeStatementQueryParams:
        """Transform the query params."""
        return FMPIncomeStatementQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FMPIncomeStatementQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> FMPAcquisition:
        """Return the raw data from the FMP endpoint."""
        # pylint: disable=import-outside-toplevel
        from openbb_fmp.utils.helpers import get_data_many

        api_key = credentials.get("fmp_api_key") if credentials else ""
        base_url = "https://financialmodelingprep.com/stable/income-statement"

        if query.period == "ttm":
            base_url += "-ttm"

        params = {"symbol": query.symbol, "limit": query.limit if query.limit is not None else 5,
                  "apikey": api_key}
        if query.period != "ttm":
            params["period"] = query.period
        url = f"{base_url}?{urlencode(params)}"

        return await get_data_many(url, with_provenance=True, typed_errors=False, **kwargs)

    @staticmethod
    def transform_data(
        query: FMPIncomeStatementQueryParams, data: FMPAcquisition, **kwargs: Any
    ) -> AnnotatedResult[list[FMPIncomeStatementData]]:
        """Return the transformed data."""
        rows = [validate_financial_result(FMPIncomeStatementData, d, provider="fmp")
                for d in data.payload]
        metadata = _income_metadata(query, rows, data.retrieved_at, len(data.payload))
        return AnnotatedResult(result=rows, metadata=metadata.as_metadata())


def _income_metadata(query, rows, retrieved_at, observed):
    """Retain reported fiscal dates and row currencies without asserting vintage safety."""
    fields = {}
    non_amounts = {"symbol", "cik", "period_ending", "fiscal_period", "fiscal_year",
                   "filing_date", "accepted_date", "reported_currency"}
    basis = {"annual": "annual", "quarter": "discrete_quarter", "ttm": "trailing_twelve_months"}.get(query.period)
    for name, field in FMPIncomeStatementData.model_fields.items():
        monetary = name not in non_amounts and "shares_outstanding" not in name
        unit = ("currency/share" if "earnings_per_share" in name else "currency") if monetary else None
        if "shares_outstanding" in name:
            unit = "shares"
        fields[name] = FinancialFieldMetadata(
            definition=field.description or name, unit=unit, scale=1 if unit else None,
            currency_field="reported_currency" if monetary else None,
            period_basis=basis, value_origin="provider_observation",
            availability="available" if any(getattr(row, name) is not None for row in rows) else "missing",
            observation_date_field="period_ending", publication_date_field="filing_date",
        )
    requested = query.limit if query.limit is not None else 5
    return FinancialResultMetadata(
        dataset="equity/fundamental/income", provider="fmp", retrieved_at=retrieved_at,
        source=FinancialSource(endpoint="income-statement-ttm" if query.period == "ttm" else "income-statement"),
        effective_query={"symbol": query.symbol, "period": query.period, "limit": requested}, fields=fields,
        bounds=FinancialBounds(requested_limit=query.limit, returned_count=len(rows),
                               effective_limit=requested if observed <= requested else None,
                               truncated=None, completeness="unknown"),
        observation_date_field="period_ending", publication_date_field="filing_date",
        limitations=["Provider completeness and restatement history are unavailable.",
                     "Filing dates do not establish point-in-time availability.",
                     "All returned baseline rows are retained; effective limit is unknown when the provider exceeds its request."],
    )
