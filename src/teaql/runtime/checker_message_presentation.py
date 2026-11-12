"""Finite model-aware locations; immutable metadata is shared per revision."""
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType
from typing import Mapping
import unicodedata

from .checker_message_catalog import _Immutable, strict_json, obj, keys, text, invalid
from .i18n import Locale, ObjectLocation

LABEL_FALLBACK = "CHECKER_MESSAGE_LABEL_FALLBACK"
GENERIC_RULE = "CHECKER_MESSAGE_GENERIC_RULE"
RENDER_FALLBACK = "CHECKER_MESSAGE_RENDER_FALLBACK"
WARNING_CODES = (LABEL_FALLBACK, GENERIC_RULE, RENDER_FALLBACK)


def sanitize(value):
    return "".join(" " if unicodedata.category(char) in ("Cc", "Cf") or char in "\u2028\u2029" else char for char in value).strip()


def _labels(value):
    result = {}
    for code, label in obj(value).items():
        locale = Locale.parse(code)
        if locale in result:
            invalid()
        result[locale] = text(label)
    return MappingProxyType(result)


_resource = strict_json(files("teaql.runtime").joinpath("checker-presentation-v1.json").read_text("utf-8"))
if _resource.get("schema") != "teaql.checker-presentation/v1":
    invalid()
WORDS = MappingProxyType({Locale.parse(code): MappingProxyType(dict(words)) for code, words in _resource["locales"].items()})
for _locale in Locale:
    for _key in ("currentObject", "utf16", "scalar", "byte"):
        _value = WORDS[_locale][_key]
        if not _value or sanitize(_value) != _value:
            invalid()


@dataclass(frozen=True, repr=False)
class _Field(_Immutable):
    name: str
    target: str | None
    labels: Mapping
    classifiers: Mapping


@dataclass(frozen=True, repr=False)
class _Entity(_Immutable):
    labels: Mapping
    fields: Mapping


@dataclass(frozen=True, repr=False)
class CheckerPresentationModel(_Immutable):
    revision: str
    _entities: Mapping
    _current: Mapping

    @classmethod
    def from_json(cls, source):
        root = obj(strict_json(source))
        keys(root, ("schema", "revision", "entities", "currentObject"))
        if root.get("schema") != "teaql.checker-model/v1":
            invalid()
        entities = {}
        for name, raw in obj(root.get("entities")).items():
            text(name)
            raw = obj(raw)
            keys(raw, ("labels", "fields"))
            if type(raw.get("fields")) is not list:
                invalid()
            fields = {}
            for raw_field in raw["fields"]:
                raw_field = obj(raw_field)
                keys(raw_field, ("name", "targetType", "labels", "classifiers", "aliases"))
                field_name = text(raw_field.get("name"))
                target = text(raw_field["targetType"]) if "targetType" in raw_field else None
                field = _Field(field_name, target, _labels(raw_field.get("labels", {})), _labels(raw_field.get("classifiers", {})))
                aliases = raw_field.get("aliases", [])
                if type(aliases) is not list:
                    invalid()
                for identity in (field_name, *(text(alias) for alias in aliases)):
                    if identity in fields:
                        invalid()
                    fields[identity] = field
            entities[name] = _Entity(_labels(raw.get("labels", {})), MappingProxyType(fields))
        current = dict(EMPTY._current)
        current.update(_labels(root.get("currentObject", {})))
        return cls(text(root.get("revision")), MappingProxyType(entities), MappingProxyType(current))

    def merge(self, other):
        if self is EMPTY:
            return other
        if other is EMPTY or self is other:
            return self
        entities = dict(self._entities)
        for name, entity in other._entities.items():
            if name in entities and entities[name] != entity:
                invalid()
            entities[name] = entity
        if self._current != other._current:
            invalid()
        return self if entities == self._entities else CheckerPresentationModel(self.revision + "+" + other.revision, MappingProxyType(entities), self._current)


EMPTY = CheckerPresentationModel("unconfigured", MappingProxyType({}), MappingProxyType({locale: WORDS[locale]["currentObject"] for locale in Locale}))


@dataclass(frozen=True, repr=False)
class _Step(_Immutable):
    identity: str | None
    field: _Field | None
    indices: tuple


@dataclass(frozen=True, repr=False)
class CheckerMessageOutput(_Immutable):
    message: str
    warnings: tuple = ()


@dataclass(frozen=True, repr=False)
class CheckerPresentation(_Immutable):
    model: CheckerPresentationModel
    origin: str | None
    shape: str
    _steps: tuple

    @classmethod
    def capture(cls, model, origin, location):
        if not isinstance(location, ObjectLocation):
            invalid()
        entity = model._entities.get(origin)
        unusual, steps = entity is None, []
        for kind, value in location.segments:
            if kind == "property":
                field = entity.fields.get(value) if entity else None
                entity = model._entities.get(field.target) if field else None
                steps.append([value, field, []])
            elif kind == "index" and type(value) is int and value >= 0:
                if not steps:
                    steps.append([None, None, []])
                    unusual = True
                steps[-1][2].append(value)
                unusual = unusual or len(steps[-1][2]) > 1
            else:
                invalid()
        unusual = unusual or not steps or bool(steps[-1][2])
        shape = "deep" if unusual or len(steps) > 2 else "one" if len(steps) == 1 else "two"
        return cls(model, origin, shape, tuple(_Step(identity, field, tuple(indices)) for identity, field, indices in steps))

    def relocate(self, location):
        return CheckerPresentation.capture(self.model, self.origin, location)

    def render(self, catalog, selection, arguments):
        locale, warnings = selection.locale, set()
        def vocabulary(labels, identity):
            label = labels.get(locale)
            if not label:
                warnings.add(LABEL_FALLBACK)
                label = labels.get(Locale.ENGLISH)
            label = sanitize(label or identity.replace("_", " "))
            return label or WORDS[locale]["currentObject"]
        def current():
            return vocabulary(self.model._current, "current object")
        entity = self.model._entities.get(self.origin)
        root = vocabulary(entity.labels, self.origin) if entity else current()
        def label(step):
            return vocabulary(step.field.labels if step.field else {}, step.field.name if step.field else step.identity or "current object")
        leaf = self._steps[-1] if self._steps else None
        args = {key: arguments[key] for key in ("system", "input", "input_len", "unit") if key in arguments}
        args["field"] = label(leaf) if leaf and leaf.identity else root
        owner_count = len(self._steps) - (1 if leaf and leaf.identity and not leaf.indices else 0)
        owners = []
        for step in self._steps[:owner_count]:
            relation = label(step) if step.identity else root
            if not step.indices:
                owners.append(catalog.reference(locale, relation))
            else:
                classifier = sanitize(step.field.classifiers.get(locale, "项" if locale in (Locale.CHINESE_SIMPLIFIED, Locale.CHINESE_TRADITIONAL) else "") if step.field else "项" if locale in (Locale.CHINESE_SIMPLIFIED, Locale.CHINESE_TRADITIONAL) else "")
                for offset, index in enumerate(step.indices):
                    owners.append(catalog.item(locale, relation if offset == 0 else current(), index, classifier))
        args["object"] = owners[0] if owners else root
        args["objectPath"] = catalog.separator(locale).join(owners) if owners else root
        return CheckerMessageOutput(selection.render(args), tuple(sorted(warnings)))
