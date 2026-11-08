"""Creation provenance is runtime state, never inferred from wire values."""
import unittest

from teaql.core.entity_creation import EntityCreationError, EntityCreationState
from teaql.core.value import Value
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots


class Entity:
    pass


class EntityCreationTests(unittest.TestCase):
    def test_only_reserved_positive_unsigned_identity_allows_insert(self):
        EntityCreationState.RESERVED.require_reserved(1)
        EntityCreationState.RESERVED.require_reserved(18446744073709551615)
        for state in EntityCreationState:
            for identity in (None, 0, -1, True, "1", 1.0, 18446744073709551616):
                with self.subTest(state=state, identity=identity):
                    with self.assertRaises(EntityCreationError) as caught:
                        state.require_reserved(identity)
                    self.assertEqual(caught.exception.code, "ENTITY_CREATION_CONTEXT_REQUIRED")
        for state in (EntityCreationState.UNMANAGED, EntityCreationState.HYDRATED):
            with self.assertRaises(EntityCreationError):
                state.require_reserved(7)

    def test_unchanged_sparse_hydration_does_not_request_creation(self):
        for state in EntityCreationState:
            state.validate_mutation("Update", None, None, False)

    def test_hydrated_mutation_requires_persisted_identity_and_version(self):
        EntityCreationState.HYDRATED.validate_mutation("Update", 7, 3, True)
        EntityCreationState.HYDRATED.validate_mutation("Delete", 7, 3, True)
        for identity, version in ((None, 3), (0, 3), (7, None), (7, True), (7, "3")):
            with self.assertRaises(EntityCreationError):
                EntityCreationState.HYDRATED.validate_mutation("Update", identity, version, True)
        from teaql.core.mutation_version import MutationVersionError, next_mutation_version
        for version in (0, -1, -(1 << 63)):
            EntityCreationState.HYDRATED.validate_mutation("Update", 7, version, True)
            with self.assertRaises(MutationVersionError) as caught:
                next_mutation_version("update", version)
            self.assertEqual(caught.exception.code, "INVALID_VERSION_STATE")
        for state in (EntityCreationState.UNMANAGED, EntityCreationState.RESERVED):
            with self.assertRaises(EntityCreationError):
                state.validate_mutation("Update", 7, 3, True)

    def test_hydrated_or_unmanaged_cannot_be_promoted_to_insert(self):
        for state in (EntityCreationState.UNMANAGED, EntityCreationState.HYDRATED):
            with self.assertRaises(EntityCreationError):
                state.validate_mutation("Create", 7, None, True)
        EntityCreationState.RESERVED.validate_mutation("Create", 7, None, True)

    def test_creation_baseline_and_hydrated_snapshot_origins_remain_distinct(self):
        entity = Entity()
        values = {"id": Value.I64(7), "name": Value.Text("same")}
        self.assertIs(LoadedScalarSnapshots.origin(entity), EntityCreationState.UNMANAGED)
        LoadedScalarSnapshots.capture(entity, values, origin=EntityCreationState.RESERVED)
        self.assertIsNone(LoadedScalarSnapshots.persisted_version(entity))
        saved = LoadedScalarSnapshots.values(entity)
        origin = LoadedScalarSnapshots.origin(entity)
        LoadedScalarSnapshots.capture(entity, {"id": Value.I64(7), "version": Value.I64(1)})
        self.assertIs(LoadedScalarSnapshots.origin(entity), EntityCreationState.HYDRATED)
        self.assertEqual(LoadedScalarSnapshots.persisted_version(entity), 1)
        LoadedScalarSnapshots.restore(entity, saved, origin=origin)
        self.assertIs(LoadedScalarSnapshots.origin(entity), EntityCreationState.RESERVED)
        self.assertEqual(LoadedScalarSnapshots.values(entity)["name"].val, "same")
        LoadedScalarSnapshots.capture(entity, values)
        entity.version = 1
        self.assertIsNone(LoadedScalarSnapshots.persisted_version(entity))
        with self.assertRaises(EntityCreationError):
            EntityCreationState.HYDRATED.validate_mutation("Update", 7,
                LoadedScalarSnapshots.persisted_version(entity), True)
        del entity.version
        self.assertEqual(vars(entity), {})


if __name__ == "__main__":
    unittest.main()
