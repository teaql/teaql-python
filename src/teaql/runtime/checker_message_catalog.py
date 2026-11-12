"""Immutable, data-only natural Checker templates shared across runtimes."""
from dataclasses import dataclass
from importlib.resources import files
import json
import re
from types import MappingProxyType
from typing import Mapping

from .i18n import Locale

SHAPES = ("one", "two", "deep")
RULES = ("checker.required", "checker.min", "checker.max", "checker.minLength", "checker.maxLength", "checker.invalid")


class _Immutable:
    def __deepcopy__(self, memo):
        return self


def invalid():
    raise ValueError("Invalid Checker message resource")


def strict_json(source):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                invalid()
            result[key] = value
        return result
    return json.loads(source, object_pairs_hook=pairs, parse_constant=lambda _: invalid())


def obj(value):
    if type(value) is not dict:
        invalid()
    return value


def text(value):
    if type(value) is not str or not value.strip():
        invalid()
    return value


def keys(value, allowed):
    if set(value) - set(allowed):
        invalid()


@dataclass(frozen=True)
class _Argument:
    name: str


@dataclass(frozen=True, repr=False)
class Template(_Immutable):
    nodes: tuple

    @classmethod
    def compile(cls, source, allowed, required):
        source = text(source)
        nodes, seen, literal, offset = [], set(), "", 0
        while offset < len(source):
            char = source[offset]
            if char in "{}" and source[offset:offset + 2] == char * 2:
                literal += char
                offset += 2
                continue
            if char == "}":
                invalid()
            if char != "{":
                literal += char
                offset += 1
                continue
            end = source.find("}", offset + 1)
            if end < 0:
                invalid()
            argument = source[offset + 1:end]
            if argument not in allowed:
                invalid()
            if literal:
                nodes.append(literal)
            nodes.append(_Argument(argument))
            literal = ""
            seen.add(argument)
            offset = end + 1
        if literal:
            nodes.append(literal)
        if set(required) - seen:
            invalid()
        return cls(tuple(nodes))

    def project(self, project):
        # Execute the projection now. Do not retain an invocation callback.
        return Template(tuple(project(node) if type(node) is str else node for node in self.nodes))

    def render(self, arguments):
        return "".join(node if type(node) is str else arguments.get(node.name, "-") for node in self.nodes)


@dataclass(frozen=True, repr=False)
class MessageSelection(_Immutable):
    locale: Locale
    template: Template

    def render(self, arguments):
        return self.template.render(arguments)

    def project(self, project):
        return MessageSelection(self.locale, self.template.project(project))


@dataclass(frozen=True, repr=False)
class _Patterns(_Immutable):
    reference: Template
    item: Template
    separator: str


@dataclass(frozen=True, repr=False)
class _Entry(_Immutable):
    rules: Mapping
    patterns: _Patterns | None


@dataclass(frozen=True, repr=False)
class CheckerMessageCatalog(_Immutable):
    _locales: Mapping
    _application: bool = False

    @classmethod
    def from_json(cls, source, *, _complete=False):
        root = obj(strict_json(source))
        keys(root, ("schema", "defaultLocale", "locales"))
        if root.get("schema") != "teaql.checker-messages/v1" or root.get("defaultLocale") != "en":
            invalid()
        entries = {}
        for code, raw in obj(root.get("locales")).items():
            locale = Locale.parse(code)
            if locale in entries:
                invalid()
            raw = obj(raw)
            keys(raw, ("rules", "locationPatterns"))
            rules = {}
            for rule, shapes in obj(raw.get("rules", {})).items():
                if not rule.startswith("checker.") or len(rule) == 8:
                    invalid()
                compiled = {}
                for shape, template in obj(shapes).items():
                    if shape not in SHAPES:
                        invalid()
                    allowed, required = {"field", "system", "input", "input_len", "unit"}, {"field"}
                    if rule in ("checker.required", "checker.invalid"):
                        allowed = {"field"}
                    elif rule in ("checker.min", "checker.max"):
                        allowed = {"field", "system", "input"}
                        required.add("system")
                    elif rule in ("checker.minLength", "checker.maxLength"):
                        allowed = {"field", "system", "input_len", "unit"}
                        required.update(("system", "input_len", "unit"))
                    if shape != "one":
                        owner = "object" if shape == "two" else "objectPath"
                        allowed.add(owner)
                        required.add(owner)
                    compiled[shape] = Template.compile(template, allowed, required)
                rules[rule] = MappingProxyType(compiled)
            patterns = None
            if "locationPatterns" in raw:
                source = obj(raw["locationPatterns"])
                keys(source, ("reference", "item", "separator"))
                reference = Template.compile(source.get("reference"), {"relation"}, {"relation"})
                item = Template.compile(source.get("item"), {"relation", "position", "ordinal", "classifier"}, {"relation"})
                if not any(isinstance(node, _Argument) and node.name in ("position", "ordinal") for node in item.nodes):
                    invalid()
                separator = text(source.get("separator"))
                if re.search(r"[{}\x00-\x1f\x7f-\x9f]", separator):
                    invalid()
                patterns = _Patterns(reference, item, separator)
            entries[locale] = _Entry(MappingProxyType(rules), patterns)
        if _complete:
            for locale in Locale:
                entry = entries.get(locale)
                if entry is None or entry.patterns is None or any(shape not in entry.rules.get(rule, {}) for rule in RULES for shape in SHAPES):
                    invalid()
        return cls(MappingProxyType(entries), not _complete)

    def lookup(self, locale, rule, shape):
        entry = self._locales.get(locale)
        template = entry.rules.get(rule, {}).get(shape) if entry else None
        return MessageSelection(locale, template) if template else None

    def override(self, locale, rule, shape):
        return self.lookup(locale, rule, shape) if self._application else None

    def select(self, locale, rule, shape):
        for candidate in (locale, Locale.ENGLISH):
            selected = self.lookup(candidate, rule, shape) or BUILTIN.lookup(candidate, rule, shape)
            if selected:
                return selected
        return BUILTIN.lookup(locale, "checker.invalid", shape)

    def _patterns(self, locale):
        entry = self._locales.get(locale)
        return entry.patterns if entry and entry.patterns else BUILTIN._locales[locale].patterns

    def project_patterns(self, locale, project):
        entry = self._locales.get(locale)
        if self is BUILTIN or not entry or not entry.patterns:
            return BUILTIN
        original = entry.patterns
        patterns = _Patterns(original.reference.project(project), original.item.project(project), project(original.separator))
        return CheckerMessageCatalog(MappingProxyType({locale: _Entry(MappingProxyType({}), patterns)}))

    def reference(self, locale, relation):
        return self._patterns(locale).reference.render({"relation": relation})

    def item(self, locale, relation, index, classifier):
        if type(index) is not int or index < 0:
            invalid()
        position = index + 1
        return self._patterns(locale).item.render({"relation": relation, "position": str(position), "ordinal": ordinal(position), "classifier": classifier})

    def separator(self, locale):
        return self._patterns(locale).separator


def ordinal(position):
    ending = "th" if 11 <= position % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
    return str(position) + ending


# Runtime composition imports these resources once, never during message rendering.
BUILTIN = CheckerMessageCatalog.from_json(files("teaql.runtime").joinpath("natural-messages-v1.json").read_text("utf-8"), _complete=True)
