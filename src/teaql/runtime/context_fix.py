"""Model-owned Context assignments in a synchronous, invocation-local frame."""
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from inspect import isawaitable, iscoroutine
from math import isfinite
from secrets import token_hex
import json

from teaql.core.value import Timestamp, Value
from .i18n import CheckException, CheckResult, ObjectLocation
from .loaded_scalar_snapshot import LoadedScalarSnapshots

_active = ContextVar("teaql_context_fix_frame", default=None)
_UNSET = object()


@dataclass(frozen=True)
class ContextFixInput:
    entity: str
    field: str
    function: str
    arguments: tuple[str, ...]
    operation: str
    now: datetime


def _fields(context, entity):
    descriptor = context.entity(entity)
    return {prop.name: (getattr(prop, "create_function", None),
                        getattr(prop, "update_function", None), prop.property_type)
            for prop in getattr(descriptor, "properties", ())
            if getattr(prop, "create_function", None) or getattr(prop, "update_function", None)}


class ContextFix:
    @staticmethod
    @contextmanager
    def scope(context, entity, record, location=None, *, operation=None, old_values=None):
        """Internal Checker boundary; caller JSON cannot create this capability."""
        if not isinstance(record, MutableMapping):
            yield
            return
        previous = _active.get()
        if previous and previous["context"] is context and previous["record"] is record:
            yield
            return
        fields = _fields(context, entity)
        operation = operation or context.get_resource("fix_operation")
        old = old_values or {}
        eligible = operation == "insert" or (operation == "update" and any(
            isinstance(name, str) and name not in fields and name not in ("id", "version") and not name.startswith("_")
            and (name not in old or not LoadedScalarSnapshots.same_value(value, old[name]))
            for name, value in record.items()))
        before = {name: deepcopy(record[name]) for name in fields if name in record}
        frame = dict(context=context, entity=entity, record=record, location=location or ObjectLocation(),
                     fields=fields, operation=operation, eligible=eligible, now=_UNSET)
        token = _active.set(frame)
        try:
            yield
        except BaseException:
            for name in fields:
                if name in before:
                    record[name] = deepcopy(before[name])
                else:
                    record.pop(name, None)
            raise
        finally:
            _active.reset(token)

    @staticmethod
    def allowed(context, record):
        frame = _active.get()
        return bool(frame and frame["context"] is context and frame["record"] is record and frame["eligible"])

    @staticmethod
    def apply(context, record, field, function, arguments=(), *, location_name=None):
        frame = _active.get()
        prefix = frame["location"] if frame and frame["context"] is context and frame["record"] is record else ObjectLocation()
        location = prefix.property(location_name or field)
        entity = frame["entity"] if frame else None
        def invalid():
            result = CheckResult("invalid_type", location, entity_type=entity,
                                message=f"Context Fix failed at {entity}.{location.model_path}")
            context.translate_check_results([result])
            return CheckException([result])
        if not frame or frame["context"] is not context or frame["record"] is not record:
            raise invalid()
        if not frame["eligible"]:
            return
        declaration = frame["fields"].get(field)
        index = 0 if frame["operation"] == "insert" else 1
        if not declaration or not declaration[index] or declaration[index] != function:
            raise invalid()
        failure = None
        try:
            if frame["now"] is _UNSET:
                frame["now"] = deepcopy(context.get_resource("fix_time"))
            now = deepcopy(frame["now"])
            resolver = context.get_resource("context_fix_resolver")
            if resolver is not None:
                value = resolver(context, ContextFixInput(entity, field, function, tuple(arguments), frame["operation"], now))
            elif function == "now":
                value = now
            elif function == "uniStr":
                value = (arguments[0] if arguments else "") + token_hex(16)
            else:
                raise ValueError("Context function requires a configured resolver")
            if isawaitable(value):
                if iscoroutine(value):
                    value.close()
                elif callable(getattr(value, "add_done_callback", None)):
                    value.add_done_callback(lambda future: None if future.cancelled() else future.exception())
                raise TypeError("prepare asynchronous Context inputs before save")
            raw = value.val if isinstance(value, Value) else value
            if not ContextFix._valid(declaration[2], raw):
                raise TypeError("invalid Context field type")
            kind = getattr(declaration[2], "name", declaration[2])
            record[field] = deepcopy(Value.Json(raw) if kind == "Json" else Value.from_any(value))
            context.record_fix_evidence(entity, location_name or field,
                "clock" if function == "now" else "context",
                "graphClock" if function == "now" else "contextFunction:" + function)
        except Exception:
            # Leave the raw exception's catch scope before raising. No cause or
            # hidden __context__ containing provider credentials is retained.
            failure = invalid()
        if failure is not None:
            raise failure from None

    @staticmethod
    def _valid(kind, value):
        if value is None:
            return True  # Required remains a generated model check.
        kind = getattr(kind, "name", kind)
        if kind in ("String", "Text", "LargeText"):
            return isinstance(value, str)
        if kind == "Bool":
            return type(value) is bool
        if kind in ("I64", "U64"):
            return type(value) is int and ((0 <= value < 1 << 64) if kind == "U64" else (-(1 << 63) <= value < 1 << 63))
        if kind == "F64":
            return type(value) is float and isfinite(value)
        if kind == "Decimal":
            return isinstance(value, Decimal) and value.is_finite()
        if kind == "Timestamp":
            return isinstance(value, datetime) or (isinstance(value, Timestamp) and type(value.millis) is int
                                                    and -(1 << 63) <= value.millis < 1 << 63)
        if kind == "Date":
            return isinstance(value, date) and not isinstance(value, datetime)
        if kind == "Time":
            return isinstance(value, time)
        if kind == "Json":
            json.dumps(value, allow_nan=False)
            return True
        return False

    @staticmethod
    def capture_graph(context, entity):
        """Internal: undo follows this graph entity's actual rekeyed identity."""
        fields = _fields(context, entity._teaql_entity_key().entity)
        session = context._graph_session
        if fields and session is not None:
            undo = entity._entity_root._capture_fields(entity._teaql_entity_key(), fields, entity._teaql_entity_key)
            session.after_rollback(undo)
