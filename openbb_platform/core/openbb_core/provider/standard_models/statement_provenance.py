"""Bounded statement evidence; fiscal labels alone do not establish duration."""

import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

SemanticKey = Literal["fiscal_year", "fiscal_period", "period_end", "filing_date", "accepted_date"]
Coverage = Literal["annual", "discrete_quarter", "year_to_date", "trailing", "unknown"]
Text = Annotated[str, Field(strict=True, max_length=200)]
ALIASES = {
    "fiscal_year": ("fiscalYear", "calendarYear"),
    "fiscal_period": ("period",), "period_end": ("date",),
    "filing_date": ("filingDate", "fillingDate"), "accepted_date": ("acceptedDate",),
}


class StatementModel(BaseModel):
    """Reject undeclared evidence without exposing validation inputs."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, allow_inf_nan=False)


def normalized_fact(key: str, value):
    """Normalize recognized aliases for comparisons while retaining their raw facts."""
    if value is None:
        return None
    if key == "fiscal_year":
        if type(value) not in (str, int):
            raise ValueError("Fiscal year requires a supplied integer or integer string")
        try:
            return TypeAdapter(int).validate_python(value)
        except ValueError:
            raise ValueError("Statement fiscal year evidence is malformed") from None
    if not isinstance(value, str) or re.search(r"[\x00-\x1f]|://", value):
        raise ValueError("Statement facts require safe recognized scalar values")
    if key == "fiscal_period":
        return value
    try:
        return TypeAdapter(datetime if key == "accepted_date" else date).validate_python(value)
    except ValueError:
        # Parser messages can embed raw source values despite hidden Pydantic inputs.
        raise ValueError("Statement date evidence is malformed") from None


class StatementFact(StatementModel):
    """Preserve supplied nulls and aliases, never a whole provider record."""

    semantic_key: SemanticKey
    source_field: Literal["fiscalYear", "calendarYear", "period", "date", "filingDate", "fillingDate", "acceptedDate"]
    value: Text | Annotated[int, Field(strict=True)] | Annotated[bool, Field(strict=True)] | None
    presence: Literal["null", "value"]
    evidence_kind: Literal["observation"] = "observation"

    @model_validator(mode="after")
    def recognized_fact(self):
        if self.source_field not in ALIASES[self.semantic_key]:
            raise ValueError("Source alias does not match semantic key")
        if (self.value is None) != (self.presence == "null"):
            raise ValueError("Fact presence does not match supplied value")
        normalized_fact(self.semantic_key, self.value)
        return self


class StatementConvention(StatementModel):
    """A reviewed provider convention can support coverage, unlike a query label."""

    semantic_key: Literal["flow_coverage"] = "flow_coverage"
    flow_coverage: Literal["annual", "discrete_quarter", "year_to_date", "trailing"]
    documentation: Annotated[str, Field(strict=True, min_length=1, max_length=200)]
    evidence_kind: Literal["provider_convention"] = "provider_convention"


class StatementPeriodRow(StatementModel):
    """Associate supplied statement identity with its position in the acquisition."""

    row_index: int = Field(ge=0, strict=True)
    source_ordinal: int = Field(ge=0, strict=True)
    fiscal_year: Annotated[int, Field(strict=True)] | None
    fiscal_period: Text | None
    period_end: date | None
    requested_frequency: Literal["q1", "q2", "q3", "q4", "fy", "ttm", "annual", "quarter"]
    flow_coverage: Coverage = "unknown"
    coverage_status: Literal["supported", "unavailable", "conflicting"] = "unavailable"
    period_start: None = None
    duration_days: None = None
    filing_date: date | None = None
    accepted_date: datetime | None = None
    restatement_status: Literal["unknown"] = "unknown"
    facts: list[StatementFact] = Field(default_factory=list, max_length=7)
    conventions: list[StatementConvention] = Field(default_factory=list, max_length=4)
    instant_dates: dict[Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=200)], date | None] = Field(default_factory=dict)

    @field_validator("fiscal_period")
    @classmethod
    def safe_fiscal_label(cls, value):
        """Keep unfamiliar reported labels without inferring their flow duration."""
        return normalized_fact("fiscal_period", value)

    @model_validator(mode="after")
    def consistent_evidence(self):
        aliases = [fact.source_field for fact in self.facts]
        if len(set(aliases)) != len(aliases):
            raise ValueError("Source facts must have unique aliases")
        conflicts = self._check_identity()
        if conflicts != (self.coverage_status == "conflicting"):
            raise ValueError("Alias conflicts require explicit conflicting coverage")
        known = self.flow_coverage != "unknown"
        if known != (self.coverage_status == "supported"):
            raise ValueError("Known coverage requires supported evidence")
        if known and (not self.conventions or any(c.flow_coverage != self.flow_coverage for c in self.conventions)):
            raise ValueError("Version 1 coverage requires a matching documented convention")
        if self.conventions and not known:
            raise ValueError("Conventions must support the declared coverage")
        for name, instant in self.instant_dates.items():
            if instant is not None and (name == "cash_at_beginning_of_period" or instant != self.period_end):
                raise ValueError("Instant date requires supported period-end association")
        return self

    def _check_identity(self):
        """Current alias precedence is explicit; conflicting legacy facts remain visible."""
        conflicts = False
        for key, aliases in ALIASES.items():
            facts = {fact.source_field: normalized_fact(key, fact.value)
                     for fact in self.facts if fact.semantic_key == key}
            if not facts:
                continue
            values = list(facts.values())
            conflicts |= any(value != values[0] for value in values[1:])
            selected = next(facts[alias] for alias in aliases if alias in facts)
            if getattr(self, key) != selected:
                raise ValueError("Statement identity does not match supplied source evidence")
        return conflicts


class StatementProvenance(StatementModel):
    """Returned indices are contiguous; acquired ordinals remain unique after clipping."""

    version: Literal[1] = 1
    rows: list[StatementPeriodRow]

    @model_validator(mode="after")
    def ordered_attribution(self):
        if [row.row_index for row in self.rows] != list(range(len(self.rows))):
            raise ValueError("Statement row indices must be contiguous")
        if len({row.source_ordinal for row in self.rows}) != len(self.rows):
            raise ValueError("Statement source ordinals must be unique")
        return self
