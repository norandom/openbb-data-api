"""Restrict discovery to the datasets maintained by QOpenBB."""

from openbb_core.provider.abstract.provider import Provider

from openbb_fmp.models.balance_sheet import FMPBalanceSheetFetcher
from openbb_fmp.models.cash_flow import FMPCashFlowStatementFetcher
from openbb_fmp.models.enterprise_values import FMPEnterpriseValuesFetcher
from openbb_fmp.models.equity_historical import FMPEquityHistoricalFetcher
from openbb_fmp.models.equity_peers import FMPEquityPeersFetcher
from openbb_fmp.models.equity_profile import FMPEquityProfileFetcher
from openbb_fmp.models.equity_search import FMPEquitySearchFetcher
from openbb_fmp.models.financial_ratios import FMPFinancialRatiosFetcher
from openbb_fmp.models.income_statement import FMPIncomeStatementFetcher
from openbb_fmp.models.key_metrics import FMPKeyMetricsFetcher

fmp_provider = Provider(
    name="fmp",
    website="https://financialmodelingprep.com",
    description="Financial Modeling Prep company research and financial input datasets.",
    credentials=["api_key"],
    fetcher_dict={
        "EquityInfo": FMPEquityProfileFetcher,
        "IncomeStatement": FMPIncomeStatementFetcher,
        "BalanceSheet": FMPBalanceSheetFetcher,
        "CashFlowStatement": FMPCashFlowStatementFetcher,
        "EquitySearch": FMPEquitySearchFetcher,
        "EquityPeers": FMPEquityPeersFetcher,
        "EquityHistorical": FMPEquityHistoricalFetcher,
        "KeyMetrics": FMPKeyMetricsFetcher,
        "FinancialRatios": FMPFinancialRatiosFetcher,
        "EnterpriseValues": FMPEnterpriseValuesFetcher,
    },
    repr_name="Financial Modeling Prep (FMP)",
    deprecated_credentials={"API_KEY_FINANCIALMODELINGPREP": "fmp_api_key"},
)
