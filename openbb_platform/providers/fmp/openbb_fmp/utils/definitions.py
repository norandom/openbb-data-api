"""Statement period vocabulary retained from FMP 1.6.1."""

from typing import Literal

FinancialStatementPeriods = Literal[
    "q1", "q2", "q3", "q4", "fy", "ttm", "annual", "quarter"
]


def validate_statement_query(symbol, period="annual", limit=5, *, allow_zero=False):
    """Bound new single-security adapters; income alone may retain zero limits."""
    from openbb_fmp.utils.errors import fail

    if (
        not isinstance(symbol, str)
        or not symbol.strip()
        or "," in symbol
        or period not in {"annual", "quarter", "quarterly"}
        or type(limit) is not int
        or not (0 if allow_zero else 1) <= limit <= 1000
    ):
        fail("invalid_parameters", typed=True)
    return {
        "symbol": symbol.strip().upper(),
        "period": "quarter" if period == "quarterly" else period,
        "limit": limit,
    }
