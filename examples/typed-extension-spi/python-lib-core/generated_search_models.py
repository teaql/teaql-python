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
            "vendorApplicationList": "VendorApplication",
        }),
    }),
    "VendorApplication": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "reference": "string",
           "legal_name": "string",
           "legalName": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "reference": "reference",
           "legal_name": "legal_name",
           "legalName": "legal_name",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
        }),
    }),
})