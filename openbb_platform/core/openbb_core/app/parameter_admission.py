"""Selected native query admission without a parallel endpoint registry."""

from copy import deepcopy
from inspect import Parameter, signature
from typing import get_args

from pydantic import AliasChoices, ValidationError

from openbb_core.app.provider_interface import ProviderInterface
from openbb_core.app.static.utils.admission_context import (
    FRAME,
    AdmissionFrame,
    InvalidParameters,
    owner,
)


def opted_in(query, provider):
    """Inherited markers never opt another variant into admission."""
    namespace = vars(query)
    return (
        provider == "fmp"
        and namespace.get("__qopenbb_strict_admission__") is True
        and namespace.get("model_config", {}).get("extra") == "forbid"
    )


def accepted_names(query):
    """Map canonical names and declared validation aliases to their owner."""
    names = {}
    for name, info in query.model_fields.items():
        names[name] = name
        alias = info.validation_alias
        aliases = alias.choices if isinstance(alias, AliasChoices) else [alias]
        for item in aliases:
            if isinstance(item, str):
                names[item] = name
    return names


def raw_values(func, args, kwargs):
    """Bind supplied values only, flattening the public variadic mapping."""
    bound = signature(func).bind_partial(*args, **kwargs)
    values = dict(bound.arguments)
    values.pop("self", None)
    for name, parameter in signature(func).parameters.items():
        if parameter.kind == Parameter.VAR_KEYWORD:
            values.update(values.pop(name, {}))
    return deepcopy(values)


def provider_choice(func, args, kwargs):
    """Establish provider independently of unrelated malformed arguments."""
    parameters = list(signature(func).parameters)
    index = parameters.index("provider") if "provider" in parameters else None
    positional = index is not None and len(args) > index
    if positional and "provider" in kwargs:
        return False, None
    choice = args[index] if positional else kwargs.get("provider")
    return choice is None or isinstance(choice, str), choice


def descriptor(container, route):
    """Read the same native descriptor and Literal order used by the emitter."""
    command_map = container._command_runner.command_map
    model = command_map.commands_model.get(route)
    command = command_map.get_command(route)
    if model is None or command is None:
        return None
    parameters = signature(command).parameters
    provider = parameters.get("provider_choices")
    if provider is None:
        return None
    dc = get_args(provider.annotation)[0]
    priorities = get_args(dc.__dataclass_fields__["provider"].type)
    return model, command, tuple(priorities)


def controls_for(func, command):
    """Financial dataclass fields are not native execution controls."""
    controls = {"provider"}
    for name, param in signature(command).parameters.items():
        if (
            name
            not in {
                "cc",
                "standard_params",
                "extra_params",
                "provider_choices",
                "kwargs",
            }
            and name in signature(func).parameters
        ):
            controls.add(name)
    if "chart" in signature(func).parameters:
        controls.add("chart")
    return frozenset(controls)


def select_frame(func, route, args, kwargs):
    """Capture eligible calls; leave omitted selection at its native execution point."""
    if not args or not hasattr(args[0], "_command_runner"):
        return None
    native = descriptor(args[0], route)
    unique, choice = provider_choice(func, args, kwargs)
    if native is None or not unique:
        return None
    model, command, priorities = native
    variants = ProviderInterface()._registry_map.original_models.get(model, {})
    candidate = variants.get("fmp", {}).get("query")
    if (
        choice not in (None, "fmp")
        or candidate is None
        or not opted_in(candidate, "fmp")
    ):
        return None
    frame = AdmissionFrame(
        args[0],
        route,
        model,
        candidate if choice == "fmp" else None,
        choice,
        choice,
        priorities,
        {},
        controls_for(func, command),
        kind="strict" if choice == "fmp" else "pending",
    )
    if frame.kind == "pending":
        try:
            frame.raw = raw_values(func, args, kwargs)
        except (TypeError, ValueError):
            return None
    return frame


def activate(frame, provider):
    """Admit original inputs only after the native body establishes selection."""
    query = (
        ProviderInterface()
        ._registry_map.original_models.get(frame.model, {})
        .get(provider, {})
        .get("query")
    )
    frame.provider = provider
    frame.query = query
    frame.kind = (
        "strict" if query is not None and opted_in(query, provider) else "baseline"
    )
    if frame.kind == "strict":
        supplied_values(frame, frame.raw)
    else:
        frame.raw.clear()
        frame.normalized.clear()


def supplied(frame, func, args, kwargs):
    """Validate only supplied financial values, never inserting defaults."""
    supplied_values(frame, raw_values(func, args, kwargs))


def supplied_values(frame, values):
    """Check a captured invocation without coercion or default insertion."""
    frame.normalized.clear()
    names = accepted_names(frame.query)
    financial = {}
    seen = set()
    for key, value in values.items():
        if key in frame.controls:
            continue
        canonical = names.get(key)
        if canonical is None or canonical in seen:
            raise InvalidParameters()
        if frame.query.model_fields[canonical].annotation is int and (
            value is None or isinstance(value, bool)
        ):
            raise InvalidParameters()
        seen.add(canonical)
        financial[key] = value
    required_absent = any(
        info.is_required() and name not in seen
        for name, info in frame.query.model_fields.items()
    )
    validated = None
    try:
        validated = frame.query.model_validate(financial)
    except ValidationError as error:
        if any(
            item["type"] != "missing" and (item["loc"] or not required_absent)
            for item in error.errors(include_input=False, include_context=False)
        ):
            raise InvalidParameters() from None
    frame.raw = financial
    if validated is not None:
        frame.normalized = {name: deepcopy(getattr(validated, name)) for name in seen}


def effective(frame, kwargs, defaults):
    """Materialize the selected schema exactly once before native execution."""
    registered = ProviderInterface()._registry_map.original_models
    query = registered.get(frame.model, {}).get(frame.provider, {}).get("query")
    if (
        query is not frame.query
        or frame.container._command_runner.command_map.commands_model.get(frame.route)
        != frame.model
    ):
        raise InvalidParameters()
    names = accepted_names(frame.query)
    values = dict(frame.raw)
    supplied_canonical = {names[key] for key in values}
    for key, value in defaults.items():
        if key in frame.controls:
            continue
        canonical = names.get(key)
        if canonical is None:
            raise InvalidParameters()
        if canonical not in supplied_canonical:
            values[key] = value
    validated = frame.query.model_validate(values).model_dump(mode="json")
    standard = kwargs.get("standard_params", {})
    kwargs["standard_params"] = {
        key: validated[key] for key in standard if key in validated
    }
    kwargs["extra_params"] = {
        key: value for key, value in validated.items() if key not in standard
    }
    frame.raw.clear()


def project_supplied(kwargs):
    """Project successful supplied normalization before native choice filtering."""
    frame = FRAME.get()
    if frame is None or frame.kind != "strict":
        return kwargs
    registered = ProviderInterface()._registry_map.original_models
    query = registered.get(frame.model, {}).get(frame.provider, {}).get("query")
    if (
        frame.owner != owner()
        or not frame.pinned
        or frame.consumed
        or frame.executing
        or kwargs.get("provider_choices", {}).get("provider") != frame.provider
        or query is not frame.query
        or not opted_in(query, frame.provider)
        or frame.container._command_runner.command_map.commands_model.get(frame.route)
        != frame.model
    ):
        raise InvalidParameters() from None
    result = dict(kwargs)
    names = accepted_names(frame.query)
    for category in ("standard_params", "extra_params"):
        if category not in result:
            continue
        params = deepcopy(result[category])
        for key in params:
            canonical = names.get(key)
            if canonical in frame.normalized:
                params[key] = deepcopy(frame.normalized[canonical])
        result[category] = params
    frame.normalized.clear()
    return result
