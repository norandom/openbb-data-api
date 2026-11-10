"""Bind allowlisted source evidence to rows before legacy alias normalization."""

from dataclasses import dataclass

from openbb_core.provider.standard_models.statement_provenance import (
    ALIASES, StatementFact, StatementPeriodRow, StatementProvenance, normalized_fact,
)
from openbb_core.provider.utils.financial_validation import validate_financial_result


@dataclass
class StatementBundle:
    """Keep each source identity attached through stable sorting and clipping."""

    row: object
    source_ordinal: int
    facts: list[StatementFact]


def statement_bundles(model, payload):
    """Capture only recognized facts before model validators can overwrite aliases."""
    bundles = []
    for ordinal, source in enumerate(payload):
        facts = []
        for semantic, aliases in ALIASES.items():
            for alias in aliases:
                if alias in source:
                    facts.append(validate_financial_result(StatementFact, {
                        "semantic_key": semantic, "source_field": alias,
                        "value": source[alias],
                        "presence": "null" if source[alias] is None else "value",
                    }, provider="fmp"))
        row = validate_financial_result(model, source, provider="fmp")
        bundles.append(StatementBundle(row, ordinal, facts))
    return bundles


def _conflicting(facts):
    """Compare normalized aliases while retaining the supplied scalar evidence."""
    for semantic in ALIASES:
        values = [normalized_fact(semantic, fact.value) for fact in facts
                  if fact.semantic_key == semantic]
        if values and any(value != values[0] for value in values[1:]):
            return True
    return False


def statement_provenance(query, bundles, fields):
    """Fiscal labels never establish duration; beginning cash has no supplied date."""
    rows = []
    for index, bundle in enumerate(bundles):
        row = bundle.row
        instants = {
            name: None if name == "cash_at_beginning_of_period" else row.period_ending
            for name, field in fields.items() if field.period_basis == "instant"
        }
        rows.append(validate_financial_result(StatementPeriodRow, {
            "row_index": index, "source_ordinal": bundle.source_ordinal,
            "fiscal_year": row.fiscal_year, "fiscal_period": row.fiscal_period,
            "period_end": row.period_ending, "requested_frequency": query.period,
            "filing_date": row.filing_date, "accepted_date": row.accepted_date,
            "coverage_status": "conflicting" if _conflicting(bundle.facts) else "unavailable",
            "facts": bundle.facts, "instant_dates": instants,
        }, provider="fmp"))
    return validate_financial_result(StatementProvenance, {"rows": rows}, provider="fmp")


def with_statement_provenance(metadata, query, bundles):
    """Validate the sidecar and envelope count together through the safe boundary."""
    payload = metadata.model_dump()
    payload["statement_provenance"] = statement_provenance(query, bundles, metadata.fields)
    return validate_financial_result(type(metadata), payload, provider="fmp")
