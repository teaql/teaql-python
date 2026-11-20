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
           "source_ip": "string",
           "sourceIp": "string",
           "last_ip": "string",
           "lastIp": "string",
           "opened_by": "string",
           "openedBy": "string",
           "changed_by": "string",
           "changedBy": "string",
           "guarded_token": "string",
           "guardedToken": "string",
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
           "source_ip": "source_ip",
           "sourceIp": "source_ip",
           "last_ip": "last_ip",
           "lastIp": "last_ip",
           "opened_by": "opened_by",
           "openedBy": "opened_by",
           "changed_by": "changed_by",
           "changedBy": "changed_by",
           "guarded_token": "guarded_token",
           "guardedToken": "guarded_token",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "catalog": "Catalog",
        }),
    }),
})