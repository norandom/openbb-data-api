"""Statement period vocabulary retained from FMP 1.6.1."""

from typing import Literal

FinancialStatementPeriods = Literal[
    "q1", "q2", "q3", "q4", "fy", "ttm", "annual", "quarter"
]
