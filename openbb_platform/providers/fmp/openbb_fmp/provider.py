"""Restrict discovery to the datasets maintained by QOpenBB."""

from openbb_core.provider.abstract.provider import Provider

from openbb_fmp.models.analyst_estimates import FMPAnalystEstimatesFetcher
from openbb_fmp.models.balance_sheet import FMPBalanceSheetFetcher
from openbb_fmp.models.balance_sheet_growth import FMPBalanceSheetGrowthFetcher
from openbb_fmp.models.cash_flow import FMPCashFlowStatementFetcher
from openbb_fmp.models.cash_flow_growth import FMPCashFlowStatementGrowthFetcher
from openbb_fmp.models.enterprise_values import FMPEnterpriseValuesFetcher
from openbb_fmp.models.equity_historical import FMPEquityHistoricalFetcher
from openbb_fmp.models.equity_peers import FMPEquityPeersFetcher
from openbb_fmp.models.equity_profile import FMPEquityProfileFetcher
from openbb_fmp.models.equity_quote import FMPEquityQuoteFetcher
from openbb_fmp.models.equity_search import FMPEquitySearchFetcher
from openbb_fmp.models.financial_ratios import FMPFinancialRatiosFetcher
from openbb_fmp.models.historical_market_cap import FmpHistoricalMarketCapFetcher
from openbb_fmp.models.income_statement import FMPIncomeStatementFetcher
from openbb_fmp.models.income_statement_growth import FMPIncomeStatementGrowthFetcher
from openbb_fmp.models.key_metrics import FMPKeyMetricsFetcher
from openbb_fmp.models.price_target import FMPPriceTargetFetcher
from openbb_fmp.models.price_target_consensus import FMPPriceTargetConsensusFetcher
from openbb_fmp.models.revenue_business_line import FMPRevenueBusinessLineFetcher
from openbb_fmp.models.revenue_geographic import FMPRevenueGeographicFetcher
from openbb_fmp.models.share_statistics import FMPShareStatisticsFetcher

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
        "AnalystEstimates": FMPAnalystEstimatesFetcher,
        "PriceTarget": FMPPriceTargetFetcher,
        "PriceTargetConsensus": FMPPriceTargetConsensusFetcher,
        "RevenueBusinessLine": FMPRevenueBusinessLineFetcher,
        "RevenueGeographic": FMPRevenueGeographicFetcher,
        "HistoricalMarketCap": FmpHistoricalMarketCapFetcher,
        "ShareStatistics": FMPShareStatisticsFetcher,
        "EquityQuote": FMPEquityQuoteFetcher,
        "IncomeStatementGrowth": FMPIncomeStatementGrowthFetcher,
        "BalanceSheetGrowth": FMPBalanceSheetGrowthFetcher,
        "CashFlowStatementGrowth": FMPCashFlowStatementGrowthFetcher,
    },
    repr_name="Financial Modeling Prep (FMP)",
    deprecated_credentials={"API_KEY_FINANCIALMODELINGPREP": "fmp_api_key"},
)
