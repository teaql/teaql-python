"""Invocation-owned generated traversal and checked input retention.

This is generated plumbing, not an alternate public mutation API. Customer Fix
runs before allocation; the final plan resolves only declared generated values.
"""
from copy import copy, deepcopy

from teaql.core.mutation import InsertCommand
from teaql.core.value import Value
from .i18n import CheckException, CheckResult, ObjectLocation
from .loaded_scalar_snapshot import LoadedScalarSnapshots


def _changed(entity=None, rule="mutation_changed_after_preparation"):
    raise CheckException([CheckResult(rule, ObjectLocation(),
        message="Graph mutation changed after input preparation",
        entity_type=entity)])


class _Reference:
    def __init__(self, target):
        self.target = target

    def value(self):
        identity = getattr(self.target, 'id', None)
        if type(identity) is not int or not 0 < identity <= 18446744073709551615:
            _changed(type(self.target).__name__)
        return Value.I64(identity)


class _GeneratedGraphPreparation:
    def __init__(self, session):
        self.session = session
        self.fixed = {}
        self.identities = {}
        self.views = {}
        self.phases = {"plan": set(), "write": set()}
        self.sealed = False

    def _active(self):
        self.session._require_active()

    def visit(self, phase, entity):
        self._active()
        seen = self.phases[phase]
        if id(entity) in seen:
            return False
        seen.add(id(entity))
        return True

    def _values(self, name, values):
        """Own scalar values without copying domain objects or their ledgers."""
        descriptor = self.session.context.entity(name)
        relations = {r.local_key: r.target_entity for r in getattr(descriptor, 'relations', ()) if not r.is_many}
        classes = self.session.context.get_resource('entity_classes') or ()
        result = {}
        for field, value in values.items():
            raw = value.val if isinstance(value, Value) else value
            if field in relations and any(type(raw) is cls and cls.__name__ == relations[field]
                                          for cls in classes if isinstance(cls, type)):
                result[field] = _Reference(raw)
            else:
                result[field] = deepcopy(value)
        return result

    @staticmethod
    def _resolve(values):
        return {name: value.value() if isinstance(value, _Reference) else deepcopy(value)
                for name, value in values.items()}

    @staticmethod
    def _same(expected, actual):
        if expected.keys() != actual.keys():
            return False
        for name, value in expected.items():
            other = actual[name]
            if isinstance(value, _Reference):
                if isinstance(other, _Reference) and value.target is other.target:
                    continue
                try:
                    value = value.value()
                except CheckException:
                    return False
            if isinstance(other, _Reference):
                try:
                    other = other.value()
                except CheckException:
                    return False
            # Business-ID wrappers are immutable str subclasses.
            left = value.val if isinstance(value, Value) else value
            right = other.val if isinstance(other, Value) else other
            if (isinstance(left, str) and type(left) is type(right) and left == right
                    and type(value) is type(other)
                    and getattr(value, '_type_hint', None) == getattr(other, '_type_hint', None)):
                continue
            if not LoadedScalarSnapshots.same_value(value, other):
                return False
        return True

    @staticmethod
    def _ledger(entity):
        return dict(entity._entity_root.current_change_set().changes()).get(entity._teaql_entity_key(), {})

    def observe(self, entity):
        self._active()
        if self.sealed:
            _changed()
        self.views.setdefault(id(entity), (entity, entity._teaql_graph_relations()))

    def admit_graph(self, root):
        """Reject distinct pending views before attaching/merging any ledger."""
        self._active()
        seen = set()
        def visit(entity):
            if id(entity) in seen:
                return
            seen.add(id(entity))
            LoadedScalarSnapshots.discard_restored_fields(entity, self.session.context)
            key = entity._teaql_entity_key()
            if entity._entity_root.has_pending(key):
                previous = self.identities.setdefault(key, entity)
                if previous is not entity:
                    _changed(key.entity, "ambiguous_mutation_view")
            for children in entity._teaql_graph_relations().values():
                for child in children:
                    visit(child)
        visit(root)

    def fix(self, entity, action, command, deferred_fields=()):
        self._active()
        if not self.session._preparing or self.sealed or id(entity) in self.fixed:
            _changed(command.entity)
        key = entity._teaql_entity_key()
        previous = self.identities.setdefault(key, entity)
        if previous is not entity:
            _changed(command.entity, "ambiguous_mutation_view")
        deferred = frozenset(deferred_fields)
        from .context_fix import ContextFix
        ContextFix.capture_graph(self.session.context, entity)
        self.session.context._check_and_fix_mutation_input(command, deferred_fields=deferred)
        for field, value in getattr(command, 'values', {}).items():
            if field not in ('id', 'version'):
                entity._entity_root.set(entity._teaql_entity_key(), field, value)
        # The normal generated admission pass also removes known-baseline
        # equal changes. Snapshot the same normalized ledger, including when
        # the Business Clock equals an already persisted update timestamp.
        LoadedScalarSnapshots.discard_restored_fields(entity, self.session.context)
        retained = copy(command)
        retained.values = self._values(command.entity, getattr(command, 'values', {}))
        if hasattr(command, 'old_values'):
            retained.old_values = deepcopy(command.old_values)
        if hasattr(command, 'id'):
            retained.id = deepcopy(command.id)
        self.fixed[id(entity)] = {
            'entity': entity, 'action': action, 'command': retained,
            'carrier': self._values(command.entity, entity._teaql_scalar_payload()),
            'ledger': self._values(command.entity, self._ledger(entity)),
            'deferred': deferred, 'initial_id': getattr(entity, 'id', None),
        }

    def finalize(self, entity, action, rebuilt):
        self._active()
        entry = self.fixed.get(id(entity))
        if not entry or entry['entity'] is not entity or action != entry['action']:
            _changed(rebuilt.entity)
        original = entry['command']
        if type(rebuilt) is not type(original) or rebuilt.entity != original.entity:
            _changed(original.entity)
        # Temporary identities may have become stable during allocation. Never
        # turn two distinct pending instances into one silently deduplicated ID.
        previous = self.identities.setdefault(entity._teaql_entity_key(), entity)
        if previous is not entity:
            _changed(original.entity, "ambiguous_mutation_view")
        if not isinstance(original, InsertCommand):
            if (not LoadedScalarSnapshots.same_value(original.id, rebuilt.id)
                    or original.expected_version_val != rebuilt.expected_version_val
                    or not self._same(original.old_values or {}, rebuilt.old_values or {})):
                _changed(original.entity)
        allowed = entry['deferred'] if isinstance(original, InsertCommand) else frozenset()
        if isinstance(original, InsertCommand) and entry['initial_id'] is None:
            allowed = allowed | {'id'}
        for baseline, live in [(entry['carrier'], entity._teaql_scalar_payload()),
                               (entry['ledger'], self._ledger(entity))]:
            before = {n: v for n, v in baseline.items() if n not in allowed}
            after = self._values(original.entity, {n: v for n, v in live.items() if n not in allowed})
            if not self._same(before, after):
                _changed(original.entity)
        final = copy(original)
        final.values = self._resolve(original.values)
        for field in allowed:
            if field in rebuilt.values:
                final.values[field] = deepcopy(rebuilt.values[field])
        context = self.session.context
        from teaql.core.mutation_version import validate_mutation_versions
        from .scalar_validation import finite_scalar_results, integral_scalar_results
        validate_mutation_versions(final)
        context._validate_mutation_fields(final.entity, final.values)
        context._validate_required_mutation_input(final)
        descriptor = context.entity(final.entity)
        results = finite_scalar_results(descriptor, final.values) + integral_scalar_results(descriptor, final.values)
        if results:
            raise CheckException(results)
        context._mutation_policy.record_preflight(final)
        self.session.capture_loaded_values(final.entity, final.values)
        return action, final

    def _state(self, entity):
        name = entity._teaql_entity_key().entity
        return (entity._action, entity._teaql_entity_key(),
                self._values(name, entity._teaql_scalar_payload()),
                self._values(name, self._ledger(entity)))

    def seal(self):
        for entity, relations in self.views.values():
            if not self._relations_equal(relations, entity._teaql_graph_relations()):
                _changed()
        self.final_states = {key: self._state(entity) for key, (entity, _) in self.views.items()}
        self.sealed = True

    @staticmethod
    def _relations_equal(before, after):
        return (before.keys() == after.keys() and all(len(items) == len(after[name])
            and all(a is b for a, b in zip(items, after[name])) for name, items in before.items()))

    def validate(self):
        if not self.sealed:
            return
        for key, (entity, relations) in self.views.items():
            if not self._relations_equal(relations, entity._teaql_graph_relations()):
                _changed()
            expected, actual = self.final_states[key], self._state(entity)
            if expected[:2] != actual[:2] or not self._same(expected[2], actual[2]) or not self._same(expected[3], actual[3]):
                _changed(entity._teaql_entity_key().entity)

    def accepted(self, entity):
        if self.sealed:
            self.final_states[id(entity)] = self._state(entity)

    def clear(self):
        self.fixed.clear()
        self.identities.clear()
        self.views.clear()
        for seen in self.phases.values():
            seen.clear()
        self.__dict__.pop('final_states', None)
