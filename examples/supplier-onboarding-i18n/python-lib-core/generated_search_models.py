from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "Warehouse": MappingProxyType({
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
            "supplierList": "Supplier",
        }),
    }),
    "Supplier": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "warehouse": "integer",
           "name": "string",
           "minimum_order_quantity": "integer",
           "minimumOrderQuantity": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "warehouse": "warehouse",
           "name": "name",
           "minimum_order_quantity": "minimum_order_quantity",
           "minimumOrderQuantity": "minimum_order_quantity",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "warehouse": "Warehouse",
        }),
    }),
})