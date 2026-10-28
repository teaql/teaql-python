"""Read-only computed query properties, never a mutation payload or loaded field."""
from copy import deepcopy
from types import MappingProxyType


class ProjectionProperties:
    __slots__ = ('__values', '__selected')

    def __init__(self, record, model_fields):
        known = frozenset(model_fields)
        self.__values = MappingProxyType({key: deepcopy(value) for key, value in record.items()
                                          if key not in known})
        self.__selected = frozenset()

    def get(self, name):
        # An absent dynamic property is null, not a NotLoaded exception.
        return deepcopy(self.__values.get(name))

    def as_dict(self):
        return deepcopy(dict(self.__values))

    def with_selected_aliases(self, names):
        """Runtime hydration capability: new immutable view, no input mutation."""
        selected = frozenset(names)
        if any(not isinstance(name, str) or not name or name not in self.__values
               for name in selected):
            raise ValueError("Selected query property was not present in the result")
        view = object.__new__(ProjectionProperties)
        view.__values, view.__selected = self.__values, selected
        return view

    def selected_values(self):
        return {name: deepcopy(self.__values[name]) for name in sorted(self.__selected)}

    def __deepcopy__(self, memo):
        # No mutable values escape this read-only snapshot.
        return self
