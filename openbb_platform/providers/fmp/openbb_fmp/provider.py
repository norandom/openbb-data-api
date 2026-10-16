"""Restrict discovery to the datasets maintained by QOpenBB."""

from openbb_core.provider.abstract.provider import Provider
from openbb_fmp.models.equity_profile import FMPEquityProfileFetcher
from openbb_fmp.models.income_statement import FMPIncomeStatementFetcher

fmp_provider = Provider(
    name="fmp",
    website="https://financialmodelingprep.com",
    description="Financial Modeling Prep profile and income statement datasets.",
    credentials=["api_key"],
    fetcher_dict={
        "EquityInfo": FMPEquityProfileFetcher,
        "IncomeStatement": FMPIncomeStatementFetcher,
    },
    repr_name="Financial Modeling Prep (FMP)",
    deprecated_credentials={"API_KEY_FINANCIALMODELINGPREP": "fmp_api_key"},
)
