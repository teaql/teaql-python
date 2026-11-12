"""Natural-message composition, projected plans and trusted customization."""
from copy import copy
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from math import isfinite
from types import MappingProxyType
import re
import sys

from .checker_message_catalog import BUILTIN, SHAPES, CheckerMessageCatalog, Template, _Argument, _Immutable
from .checker_message_presentation import (
    EMPTY, WORDS, WARNING_CODES, GENERIC_RULE, RENDER_FALLBACK,
    CheckerMessageOutput, CheckerPresentation, CheckerPresentationModel, sanitize,
)
from .i18n import Locale, ObjectLocation


@dataclass(frozen=True, repr=False)
class CheckerMessageRequest(_Immutable):
    presentation: CheckerPresentation
    catalog: CheckerMessageCatalog
    selection: object
    arguments: object


def standard_checker_message_renderer(request):
    return request.presentation.render(request.catalog, request.selection, request.arguments)


def default_checker_message_warning(code):
    print(code, file=sys.stderr)


@dataclass(frozen=True, repr=False)
class CheckerMessageConfiguration(_Immutable):
    model: CheckerPresentationModel
    catalog: CheckerMessageCatalog
    legacy: object
    locale: Locale
    renderer: object = standard_checker_message_renderer
    warning: object = default_checker_message_warning


@dataclass(frozen=True, repr=False)
class _Prepared(_Immutable):
    selection: object
    catalog: CheckerMessageCatalog
    legacy: Template | None = None
    generic: bool = False
    application: bool = False


@dataclass(frozen=True, repr=False)
class _Plan(_Immutable):
    entries: object = None
    literal: str | None = None

    def project(self, project):
        if self.literal is not None:
            return _Plan(literal=project(self.literal))
        # A new batch can classify a formerly public custom literal as a
        # sensitive sibling. Reproject retained custom nodes, not built-in rule
        # vocabulary or numeric/position arguments; never reopen raw resources.
        return _Plan(MappingProxyType({key: _Prepared(
            item.selection.project(project) if item.application and item.selection else item.selection,
            item.catalog.project_patterns(item.selection.locale if item.selection else key[0], project),
            item.legacy.project(project) if item.legacy else None, item.generic, item.application)
            for key, item in self.entries.items()}))

    def render(self, snapshot, result, locale, arguments):
        if self.literal is not None:
            return CheckerMessageOutput(self.literal)
        item = self.entries[(locale, snapshot.shape)]
        if item.legacy is not None:
            return CheckerMessageOutput(item.legacy.render({**arguments, "location": result.location.native_path}))
        arguments = {**arguments, "unit": WORDS[item.selection.locale]["scalar"]}
        output = snapshot.render(item.catalog, item.selection, arguments)
        return CheckerMessageOutput(output.message, (*output.warnings, GENERIC_RULE)) if item.generic else output


@dataclass(frozen=True, repr=False)
class _Binding(_Immutable):
    snapshot: CheckerPresentation
    plan: _Plan | None = None


def bind_origin(results, model, origin):
    owned = []
    for result in results:
        result = copy(result)
        previous = getattr(result, "_natural_presentation", None)
        result._natural_presentation = _Binding(CheckerPresentation.capture(model, origin, result.location), previous.plan if previous else None)
        owned.append(result)
    return owned


def _legacy(template, project):
    nodes = []
    for part in re.split(r"(\{(?:location|system|input|input_len)\})", template):
        nodes.append(_Argument(part[1:-1]) if re.fullmatch(r"\{(?:location|system|input|input_len)\}", part) else project(part))
    return Template(tuple(nodes))


def _prepare(config, rule, project):
    entries, patterns = {}, {}
    for locale in Locale:
        for shape in SHAPES:
            selection, legacy, application = None, None, False
            for candidate in (locale, Locale.ENGLISH):
                selection = config.catalog.override(candidate, rule, shape)
                if selection:
                    application = True
                    break
                raw = config.legacy.application_message(candidate, rule)
                if raw is not None:
                    legacy = _legacy(raw, project)
                    break
                selection = BUILTIN.lookup(candidate, rule, shape)
                if selection:
                    break
            generic = selection is None and legacy is None
            if generic:
                selection = BUILTIN.select(locale, "checker.invalid", shape)
            if selection and application:
                selection = selection.project(project)
            effective = selection.locale if selection else locale
            if effective not in patterns:
                patterns[effective] = config.catalog.project_patterns(effective, project)
            entries[(locale, shape)] = _Prepared(selection, patterns[effective], legacy, generic, application)
    return _Plan(MappingProxyType(entries))


def _scalar(value):
    if value is None or type(value) in (str, int, bool):
        return sanitize(value) if type(value) is str else str(value)
    if type(value) is float and isfinite(value):
        return str(value)
    if type(value) is Decimal and value.is_finite():
        return str(value)
    if type(value) in (date, datetime, time):
        return value.isoformat()
    return "[value omitted]"


def render_natural(config, result, *, input_value, system_value, length, secrets, rule, seen, forced=None):
    from .checker_privacy import _scrub
    previous = getattr(result, "_natural_presentation", None)
    model = forced[0] if forced else previous.snapshot.model if previous else config.model
    origin = forced[1] if forced else previous.snapshot.origin if previous else None
    def warn(code):
        code = code if code in WARNING_CODES else RENDER_FALLBACK
        if code not in seen:
            seen.add(code)
            try:
                config.warning(code)
            except Exception:
                pass
    try:
        snapshot = CheckerPresentation.capture(model, origin, result.location)
    except Exception:
        warn(RENDER_FALLBACK)
        snapshot = CheckerPresentation.capture(EMPTY, None, ObjectLocation())
    locale = Locale.parse(config.locale)  # Invalid explicit selections remain typed errors.
    arguments = MappingProxyType({"input": _scalar(input_value), "system": _scalar(system_value), "input_len": str(length), "unit": WORDS[locale]["scalar"]})
    plan = previous.plan if previous else None
    if plan is not None and secrets:
        plan = plan.project(lambda literal: _scrub(literal, secrets))
    try:
        if plan is None:
            plan = _prepare(config, rule, lambda literal: _scrub(literal, secrets))
            item = plan.entries[(locale, snapshot.shape)]
            if config.renderer is not standard_checker_message_renderer and item.legacy is None:
                if item.generic:
                    warn(GENERIC_RULE)
                output = config.renderer(CheckerMessageRequest(snapshot, item.catalog, item.selection,
                    MappingProxyType({**arguments, "unit": WORDS[item.selection.locale]["scalar"]})))
                if not isinstance(output, CheckerMessageOutput):
                    raise TypeError("Checker renderer must return CheckerMessageOutput")
                output = CheckerMessageOutput(_scrub(output.message, secrets), output.warnings)
                plan = _Plan(literal=output.message)
            else:
                output = plan.render(snapshot, result, locale, arguments)
        else:
            output = plan.render(snapshot, result, locale, arguments)
        if type(output.message) is not str or not output.message.strip():
            raise ValueError("Checker renderer returned an empty message")
        for code in output.warnings:
            warn(code)
    except Exception:
        warn(RENDER_FALLBACK)
        output = snapshot.render(BUILTIN, BUILTIN.select(locale, "checker.invalid", snapshot.shape), {})
        plan = _Plan(literal=output.message)
        for code in output.warnings:
            warn(code)
    return output.message, _Binding(snapshot, plan)
