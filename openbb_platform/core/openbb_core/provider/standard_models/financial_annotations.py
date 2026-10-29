"""Class-owned static declarations; observed financial metadata stays runtime-owned."""

from typing import Literal, get_args

from openbb_core.provider.standard_models.financial_metadata import (
    FinancialBounds,
    FinancialFieldMetadata,
    FinancialMetadataModel,
    FinancialResultMetadata,
    Identifier,
)
from pydantic import BaseModel, Field, field_validator, model_validator

QUERY_ANNOTATION_ATTRIBUTE = "financial_query_annotation"
DATA_ANNOTATION_ATTRIBUTE = "financial_data_annotation"
FINANCIAL_METADATA_LOCATION = "extra.results_metadata.__qopenbb_financial__"


class MissingFinancialAnnotation(ValueError):
    """The owning class has not declared its financial contract."""


class InvalidFinancialAnnotation(ValueError):
    """A declaration is malformed or references an absent canonical field."""


class FinancialFieldTemplate(FinancialFieldMetadata):
    """Reuse result semantics; bind definitions from the owning Field description."""

    definition: str | None = Field(default=None, min_length=1)


class ProceduralBounds(FinancialMetadataModel):
    """Bounds enforced outside ordinary Pydantic field constraints."""

    max_calendar_years: int | None = Field(default=None, gt=0, strict=True)
    max_symbols: int | None = Field(default=None, gt=0, strict=True)


class ResponsePolicy(FinancialMetadataModel):
    """Income compatibility preserves limit zero and excess upstream rows."""

    mode: Literal["clip", "provider", "income_compatibility"]
    max_rows: int | None = Field(default=None, gt=0, strict=True)
    limit_parameter: Identifier | None = None

    @model_validator(mode="after")
    def consistent_cap(self):
        """Reserve fixed caps for explicit local clipping."""
        caps = int(self.max_rows is not None) + int(self.limit_parameter is not None)
        if caps != (1 if self.mode == "clip" else 0):
            raise ValueError("Clipping requires one cap; other policies cannot claim a cap")
        return self


def _runtime_properties(paths: list[str]) -> list[str]:
    roots = FinancialResultMetadata.model_fields
    nested = {"fields": FinancialFieldMetadata, "bounds": FinancialBounds}
    for path in paths:
        parts = path.split(".")
        if parts[0] not in roots or len(parts) > 2:
            raise ValueError("Unknown runtime metadata property")
        if len(parts) == 2 and (
            parts[0] not in nested or parts[1] not in nested[parts[0]].model_fields
        ):
            raise ValueError("Unknown nested runtime metadata property")
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate runtime metadata properties")
    return paths


class FinancialQueryAnnotation(FinancialMetadataModel):
    """Ordinary defaults, choices and requiredness remain on the query model."""

    provider_policy: Literal["explicit", "baseline_default"]
    procedural_bounds: ProceduralBounds = Field(default_factory=ProceduralBounds)
    response_policy: ResponsePolicy
    runtime_properties: list[Identifier] = Field(default_factory=list)

    _validate_runtime_properties = field_validator("runtime_properties")(_runtime_properties)


class FinancialDataAnnotation(FinancialMetadataModel):
    """Templates use canonical Python names; runtime properties disclose potential resolution."""

    fields: dict[Identifier, FinancialFieldTemplate] = Field(default_factory=dict)
    runtime_properties: list[Identifier] = Field(default_factory=list)
    dynamic_fields: bool = False

    _validate_runtime_properties = field_validator("runtime_properties")(_runtime_properties)


def _declaration(model: type[BaseModel], attribute: str, expected: type):
    if not hasattr(model, attribute):
        raise MissingFinancialAnnotation(f"Missing {attribute}")
    value = getattr(model, attribute)
    if not isinstance(value, expected):
        raise InvalidFinancialAnnotation(f"Invalid {attribute} type")
    try:
        return expected.model_validate(value.model_dump()).model_copy(deep=True)
    except ValueError as exc:
        raise InvalidFinancialAnnotation(f"Invalid {attribute}") from exc


def _canonical_fields(model: type[BaseModel]) -> dict:
    fields = {}
    for name, field in model.model_fields.items():
        if field.exclude is True:
            continue
        fields[name] = field
    return fields


def bind_query_annotation(model: type[BaseModel]) -> FinancialQueryAnnotation:
    """Return an independently validated declaration without copying model schemas."""
    annotation = _declaration(model, QUERY_ANNOTATION_ATTRIBUTE, FinancialQueryAnnotation)
    fields = _canonical_fields(model)
    if (annotation.procedural_bounds.max_calendar_years is not None
            and not {"start_date", "end_date"}.issubset(fields)):
        raise InvalidFinancialAnnotation("Calendar-year bounds require start_date/end_date")
    if (annotation.procedural_bounds.max_symbols is not None
            and not {"symbol", "symbols"}.intersection(fields)):
        raise InvalidFinancialAnnotation("Symbol bounds require symbol/symbols")
    parameter = annotation.response_policy.limit_parameter
    if parameter is not None:
        field = fields.get(parameter)
        types = set(get_args(field.annotation) or (field.annotation,)) if field else set()
        if int not in types or not types.issubset({int, type(None)}):
            raise InvalidFinancialAnnotation("Clipping parameter requires a modeled integer count")
    return annotation


def bind_data_annotation(model: type[BaseModel]) -> FinancialDataAnnotation:
    """Validate canonical Python names used by native non-alias responses."""
    annotation = _declaration(model, DATA_ANNOTATION_ATTRIBUTE, FinancialDataAnnotation)
    fields = _canonical_fields(model)
    if set(annotation.fields) != set(fields):
        raise InvalidFinancialAnnotation("Templates must cover exactly the canonical static fields")
    for template in annotation.fields.values():
        for attribute in ("currency_field", "observation_date_field", "valuation_date_field",
                          "publication_date_field"):
            reference = getattr(template, attribute)
            if reference is not None and reference not in fields:
                raise InvalidFinancialAnnotation("Metadata references an absent canonical field")
    return annotation


def render_field_templates(model: type[BaseModel]) -> dict[str, FinancialFieldMetadata]:
    """Render independent result templates; adapters fill observed values afterward."""
    annotation = bind_data_annotation(model)
    fields = _canonical_fields(model)
    rendered = {}
    for name, template in annotation.fields.items():
        description = fields[name].description
        if not description:
            raise InvalidFinancialAnnotation("Financial fields require a Field description")
        if template.definition is not None and template.definition != description:
            raise InvalidFinancialAnnotation("Template definition differs from Field description")
        values = template.model_dump()
        values["definition"] = description
        rendered[name] = FinancialFieldMetadata.model_validate(values)
    return rendered
