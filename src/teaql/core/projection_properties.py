"""Read-only computed query properties, never a mutation payload or loaded field."""
from copy import deepcopy
from types import MappingProxyType


class ProjectionProperties:
    __slots__ = ('__values',)

    def __init__(self, record, model_fields):
        known = frozenset(model_fields)
        self.__values = MappingProxyType({key: deepcopy(value) for key, value in record.items()
                                          if key not in known})

    def get(self, name):
        # An absent dynamic property is null, not a NotLoaded exception.
        return deepcopy(self.__values.get(name))

    def as_dict(self):
        return deepcopy(dict(self.__values))

    def __deepcopy__(self, memo):
        # No mutable values escape this read-only snapshot.
        return self
