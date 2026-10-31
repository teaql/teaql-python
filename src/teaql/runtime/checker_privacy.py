"""Invocation-owned Checker presentations; no Context or raw-secret cache."""
from collections.abc import Mapping
from copy import copy
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
import re

from teaql.core.value import Timestamp, Value
from .audit import _mask
from .log_privacy import REDACTED, credential_name, plaintext_enabled


@dataclass(frozen=True, repr=False)
class _Presentation:
    input_signature: str
    system_signature: str
    message_signature: str
    safe_input: object
    safe_system: object
    safe_message: object
    input_length: int
    model_mask: bool
    credential: bool
    automatic_message: bool


class _CheckBatch(list):
    # Raw strings live only in this invocation's argument, never in Context,
    # result presentation metadata or the exception's retained violations.
    __slots__ = ("owner", "scope")

    def __init__(self, results, owner, scope):
        super().__init__(clone(result) for result in results)
        self.owner, self.scope = owner, scope
        for result in self:
            if not result.entity_type or not result.entity_type.strip():
                result.entity_type = owner


def clone(result):
    # Copy the seven public fields and private safe presentation, not their
    # caller-owned nested values. Projection makes independent value snapshots.
    return copy(result)


def _raw(value, seen=None, depth=0):
    if isinstance(value, Value):
        value = value.val
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        return value if isfinite(value) else str(value)
    if type(value) is Decimal:
        return value if value.is_finite() else str(value)
    if type(value) in (date, datetime, time):
        return value
    if isinstance(value, Timestamp):
        return value.millis
    if isinstance(value, Enum):
        return _raw(value.value, seen, depth + 1)
    if depth >= 32:
        return REDACTED
    seen = set() if seen is None else seen
    if id(value) in seen:
        return REDACTED
    seen.add(id(value))
    try:
        if isinstance(value, Mapping):
            return {k if isinstance(k, str) else "[key]": _raw(v, seen, depth + 1)
                    for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_raw(v, seen, depth + 1) for v in value]
        if is_dataclass(value) and not isinstance(value, type):
            return {f.name: _raw(getattr(value, f.name), seen, depth + 1) for f in fields(value)}
        return REDACTED  # Do not call arbitrary application __str__/__repr__.
    finally:
        seen.remove(id(value))


def _signature(value):
    def typed(v):
        if type(v) is Decimal:
            return {"$decimal": str(v)}
        if type(v) in (date, datetime, time):
            return {"$" + type(v).__name__: v.isoformat()}
        raise TypeError("unexpected diagnostic snapshot type")
    encoded = json.dumps(value, default=typed, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return sha256(encoded.encode()).hexdigest()


def _spellings(name):
    words = name.split("_")
    camel = words[0] + "".join(w[:1].upper() + w[1:] for w in words[1:])
    return {name, camel, camel[:1].upper() + camel[1:]}


def _property(entity, name):
    return next((p for p in getattr(entity, "properties", ())
                 if name in _spellings(p.name) | {p.column_name_val}), None)


def _relation(entity, name):
    return next((r for r in getattr(entity, "relations", ()) if name in _spellings(r.name)), None)


def _field_policy(entity, name):
    prop = _property(entity, name)
    names = {name} | ({prop.name, prop.column_name_val} if prop else set())
    credential = any(credential_name(n) for n in names) or getattr(prop, "log_policy_val", None) == "credential"
    masked = bool(names & set(getattr(entity, "audit_mask_fields_val", ()))) or getattr(prop, "log_policy_val", None) == "masked"
    return masked, credential


def _at(entity, segments, resolve):
    names = [str(value) for kind, value in segments if kind == "property"]
    masked = False
    credential = any(credential_name(n) for n in names)
    current = entity
    for index, name in enumerate(names):
        relation = _relation(current, name)
        m, c = _field_policy(current, name)
        masked, credential = masked or m, credential or c
        if relation:
            # A real relation wins over a declaring type's same-named scalar.
            current = resolve(relation.target_entity) if resolve else None
        elif _property(current, name):
            # A scalar JSON field is not another namespace of its owner.
            current = None
        else:
            if index == 0 and len(names) > 1:
                # Declaring child types can carry an already-prefixed graph path.
                m, c = _field_policy(current, names[-1])
                masked, credential = masked or m, credential or c
            current = None
    return masked, credential, current


def _masked(value):
    if value is None or value == REDACTED:
        return value
    if isinstance(value, list):
        return [_masked(v) for v in value]
    if isinstance(value, dict):
        return REDACTED
    return _mask(str(value))  # Only normalized, known native scalar types reach here.


def _project_value(value, entity=None, resolve=None, *, allow=False, masked=False, credential=False):
    if value is None:
        return None
    if credential:
        return REDACTED
    if masked and not allow:
        return _masked(value)
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            m, c = _field_policy(entity, key)
            relation = _relation(entity, key)
            target = resolve(relation.target_entity) if relation and resolve else None
            result[key] = _project_value(child, target, resolve, allow=allow, masked=m, credential=c)
        return result
    if isinstance(value, list):
        return [_project_value(v, entity, resolve, allow=allow) for v in value]
    return value


def _changed_strings(raw, safe):
    if isinstance(raw, str):
        return [raw] if raw and raw != safe else []
    if isinstance(raw, dict):
        return [s for key, value in raw.items() for s in _changed_strings(value, safe.get(key) if isinstance(safe, dict) else None)]
    if isinstance(raw, list):
        return [s for i, value in enumerate(raw) for s in _changed_strings(value, safe[i] if isinstance(safe, list) and i < len(safe) else None)]
    return []


def capture(record, resolve, owner):
    """Return force-safe and debug-sensitive strings as invocation arguments."""
    value = _raw(record)
    entity = resolve(owner) if resolve else None
    safe = _project_value(value, entity, resolve)
    debug = _project_value(value, entity, resolve, allow=True)
    return tuple(_changed_strings(value, safe)), tuple(_changed_strings(value, debug))


def _scrub(text, secrets):
    if not isinstance(text, str):
        return text
    variants = set()
    for secret in secrets:
        if not secret:
            continue
        variants.add(secret)
        variants.add(json.dumps(secret, ensure_ascii=True)[1:-1])
        variants.add(json.dumps(secret, ensure_ascii=False)[1:-1])
    if not variants:
        return text
    return re.sub("|".join(re.escape(s) for s in sorted(variants, key=len, reverse=True)), lambda _: REDACTED, text)


def _system(value, secrets, credential=False):
    # Numeric bounds and public rule vocabulary are not secret input echoes.
    if isinstance(value, str):
        return REDACTED if credential else _scrub(value, secrets)
    if isinstance(value, dict):
        return {k: _system(v, secrets, credential or credential_name(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_system(v, secrets, credential) for v in value]
    return value


def _rule_key(rule):
    rule = getattr(rule, "value", rule)
    keys = {"REQUIRED": "required", "MIN": "min", "MAX": "max", "MIN_STR_LEN": "minLength",
            "MIN_LENGTH": "minLength", "MAX_STR_LEN": "maxLength", "MAX_LENGTH": "maxLength"}
    return "checker." + keys.get(str(rule).upper(), str(rule).lower())


def _render(template, values, secrets, builtin):
    # Scrub only free-form literals, before typed substitutions. A password "1"
    # cannot redact a numeric bound 1000, canonical path or built-in vocabulary.
    pattern = re.compile(r"\{(location|system|input|input_len)\}")
    parts, start = [], 0
    for match in pattern.finditer(template):
        literal = template[start:match.start()]
        parts.extend([literal if builtin else _scrub(literal, secrets), str(values[match[1]])])
        start = match.end()
    literal = template[start:]
    parts.append(literal if builtin else _scrub(literal, secrets))
    return "".join(parts)


def project(result, *, resolve=None, owner=None, scope=((), ()), catalog=None, locale=None, force_safe=False):
    from .i18n import I18nCatalog
    output = clone(result)
    raw_input, raw_system = _raw(result.input_value), _raw(result.system_value)
    previous = getattr(result, "_presentation", None)
    input_sig, system_sig = _signature(raw_input), _signature(raw_system)
    same_input = previous is not None and input_sig == previous.input_signature
    same_system = previous is not None and system_sig == previous.system_signature
    message_sig = _signature(result.message)
    same_message = previous is not None and message_sig == previous.message_signature
    length = previous.input_length if same_input else len(raw_input) if isinstance(raw_input, (str, list, dict)) else 0
    allow = not force_safe and plaintext_enabled()
    segments = result.location.segments
    masked = previous.model_mask if previous else False
    credential = previous.credential if previous else False
    targets = []
    for name in dict.fromkeys(n for n in (owner, result.entity_type) if n):
        m, c, target = _at(resolve(name) if resolve else None, segments, resolve)
        masked, credential = masked or m, credential or c
        targets.append(target)
    credential = credential or any(credential_name(str(v)) for k, v in segments if k == "property")
    safe_input = _raw(previous.safe_input) if same_input else _raw(raw_input)
    display_input = _raw(raw_input)
    for target in targets or [None]:
        safe_input = _project_value(safe_input, target, resolve, masked=masked, credential=credential)
        display_input = _project_value(display_input, target, resolve, allow=allow, masked=masked, credential=credential)
    if not allow:
        display_input = _raw(safe_input)
    safe_secrets = tuple(scope[0]) + tuple(_changed_strings(raw_input, safe_input))
    display_secrets = tuple(scope[1] if allow else scope[0]) + tuple(_changed_strings(raw_input, display_input))
    safe_system = _system(_raw(previous.safe_system) if same_system else raw_system, safe_secrets, credential)
    display_system = _system(raw_system, display_secrets, credential) if allow else _raw(safe_system)
    safe_secrets += tuple(_changed_strings(raw_system, safe_system))
    display_secrets += tuple(_changed_strings(raw_system, display_system))
    automatic = result.message is None or bool(same_message and previous.automatic_message)
    if catalog is not None and automatic:
        key = _rule_key(result.rule_id)
        template = catalog.message(locale, key)
        builtin = template == I18nCatalog.builtin().message(locale, key)
        values = {"location": result.location.native_path, "system": safe_system, "input": safe_input, "input_len": length}
        safe_message = _render(template, values, safe_secrets, builtin)
        values.update(system=display_system, input=display_input)
        display_message = _render(template, values, display_secrets, builtin)
    else:
        # A previously unbound/plain diagnostic can acquire a stricter actual
        # request-owner policy. Cached safe text is not an authority to bypass it.
        safe_message = _scrub(previous.safe_message if same_message else result.message, safe_secrets)
        display_message = _scrub(result.message, display_secrets) if allow else safe_message
    output.input_value, output.system_value, output.message = display_input, display_system, display_message
    output._presentation = _Presentation(_signature(display_input), _signature(display_system), _signature(display_message),
                                         _raw(safe_input), _raw(safe_system), safe_message, length, masked, credential, automatic)
    return output


def translate(catalog, result, locale, *, resolve=None, owner=None, scope=((), ())):
    output = project(result, resolve=resolve, owner=owner, scope=scope, catalog=catalog, locale=locale)
    result.input_value, result.system_value, result.message = output.input_value, output.system_value, output.message
    result._presentation = output._presentation
    return result
