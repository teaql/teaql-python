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
            "customerList": "Customer",
        }),
    }),
    "Customer": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "email": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "email": "email",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
            "customerContactList": "CustomerContact",
        }),
    }),
    "CustomerContact": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer": "integer",
           "channel": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer": "customer",
           "channel": "channel",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer": "Customer",
        }),
    }),
})