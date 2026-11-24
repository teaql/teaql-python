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
            "purchaseOrderList": "PurchaseOrder",
        }),
    }),
    "PurchaseOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "supplier": "string",
           "order_number": "string",
           "orderNumber": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "supplier": "supplier",
           "order_number": "order_number",
           "orderNumber": "order_number",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
        }),
    }),
})