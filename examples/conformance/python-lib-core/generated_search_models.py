from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "Platform": MappingProxyType({
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
            "workItemList": "WorkItem",
        }),
    }),
    "WorkItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "title": "string",
           "description": "string",
           "platform": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "title": "title",
           "description": "description",
           "platform": "platform",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
        }),
    }),
})