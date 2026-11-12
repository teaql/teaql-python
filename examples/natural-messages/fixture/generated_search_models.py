from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "Catalog": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "name": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "name": "name",
           "version": "version",
        }),
        "relations": MappingProxyType({
            "entryList": "Entry",
        }),
    }),
    "Entry": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "catalog": "integer",
           "name": "string",
           "born_at": "timestamp",
           "bornAt": "timestamp",
           "touched_at": "timestamp",
           "touchedAt": "timestamp",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "catalog": "catalog",
           "name": "name",
           "born_at": "born_at",
           "bornAt": "born_at",
           "touched_at": "touched_at",
           "touchedAt": "touched_at",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "catalog": "Catalog",
        }),
    }),
})