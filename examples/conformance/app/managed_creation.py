"""Managed creation boundaries using this repository and its generated example."""
import asyncio
import json
import pathlib
import sys
import unittest

EXAMPLE = pathlib.Path(__file__).resolve().parents[1]
REPO = EXAMPLE.parents[1]
sys.path[:0] = [str(EXAMPLE), str(REPO / "src")]
import teaql
assert pathlib.Path(teaql.__file__).resolve() == REPO / "src/teaql/__init__.py"
from Q import Q
from models.work_item import WorkItem
from runtime_module import GENERATED_RUNTIME_MODULE

failure = RuntimeError("controlled managed creation reservation failure")


class Allocator:
    def __init__(self, *values):
        self.values, self.calls = iter(values), []

    async def next_id(self, entity):
        self.calls.append(entity)
        assert entity == "WorkItem"
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value

    async def ensure_id_floor(self, entity, floor):
        raise AssertionError("The allocation-only probe must not advance an ID floor")


def context(*values):
    selected = Allocator(*values)
    return GENERATED_RUNTIME_MODULE.into_context().with_internal_id_allocator(selected), selected


def request():
    return Q.work_items().comment("Prepare a managed work item").purpose("Verify the creation boundary")


def loaded():
    return WorkItem.from_json('{"id":"77","version":"3","title":"loaded","description":null,"platform":"1"}')


class ManagedCreation(unittest.IsolatedAsyncioTestCase):
    async def test_public_constructor_cannot_bypass_context(self):
        for kwargs in ({}, {"id": 77}, {"title": "unallocated"}):
            with self.assertRaises(Exception) as caught:
                WorkItem(**kwargs)
            self.assertEqual(getattr(caught.exception, "code", None), "ENTITY_CREATION_CONTEXT_REQUIRED")

    async def test_initializer_observes_reserved_positive_identity(self):
        ctx, ids = context(701)
        seen = []
        ctx.register_entity_initializer("WorkItem", lambda _context, entity: seen.append(entity.id))
        entity = await request().new_entity(ctx)
        self.assertEqual(entity.id, 701)
        self.assertEqual(seen, [701])
        self.assertEqual(ids.calls, ["WorkItem"])

    async def test_selected_allocator_failure_zero_recovery_and_independent_ledgers(self):
        ctx, ids = context(701, 702, failure, 0, 705)
        first, second = await request().new_entity(ctx), await request().new_entity(ctx)
        self.assertEqual((first.id, second.id), (701, 702))
        self.assertIsNot(first._entity_root, second._entity_root)
        first.update_title("only first graph")
        self.assertNotIn("title", dict(second._entity_root.current_change_set().changes()).get(second._teaql_entity_key(), {}))
        self.assertTrue(first._entity_root.has_pending(first._teaql_entity_key()))
        with self.assertRaises(RuntimeError) as caught:
            await request().new_entity(ctx)
        self.assertIs(caught.exception, failure)
        with self.assertRaises(ValueError):
            await request().new_entity(ctx)
        self.assertEqual(len(ctx.managed_entities()), 2)
        recovered = await request().new_entity(ctx)
        self.assertEqual(recovered.id, 705)
        self.assertEqual(ids.calls, ["WorkItem"] * 5)
        self.assertEqual(len(ctx.managed_entities()), 3)
        self.assertEqual(first.id, 701)

    async def test_existing_json_hydration_is_read_only(self):
        entity = loaded()
        self.assertEqual((entity.id, entity.version), (77, 3))
        self.assertEqual(entity._action, "Update")
        self.assertFalse(entity._entity_root.has_pending(entity._teaql_entity_key()))
        self.assertIn("description", entity._loaded_fields)
        self.assertIsNone(entity.description)

    async def test_sparse_json_hydration_is_not_creation(self):
        entity = WorkItem.from_json("{}")
        self.assertIsNone(entity.id)
        self.assertEqual(entity._action, "Update")
        self.assertFalse(entity._entity_root.has_pending(entity._teaql_entity_key()))
        self.assertIsNone(entity._ledger_id)

    async def test_hydrated_snapshot_cannot_be_promoted_to_insert(self):
        entity = loaded()
        with self.assertRaises(Exception) as caught:
            entity._teaql_force_create()
        self.assertEqual(getattr(caught.exception, "code", None), "ENTITY_CREATION_CONTEXT_REQUIRED")
        self.assertEqual(entity._action, "Update")
        self.assertFalse(entity._entity_root.has_pending(entity._teaql_entity_key()))


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.observed.append({"test": test._testMethodName, "outcome": "pass"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.observed.append({"test": test._testMethodName, "outcome": "fail"})

    def addError(self, test, error):
        super().addError(test, error)
        self.observed.append({"test": test._testMethodName, "outcome": "error"})


if __name__ == "__main__":
    rounds = []
    for number in (1, 2):
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(ManagedCreation))
        assert len(result.observed) == 6
        rounds.append({"round": number, "outcomes": result.observed})
    print("PYTHON_MANAGED_CREATION=" + json.dumps({"rounds": rounds}, sort_keys=True))
    raise SystemExit(0 if all(q["outcome"] == "pass" for r in rounds for q in r["outcomes"]) else 1)
