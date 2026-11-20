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
            "purchaseOrderList": "PurchaseOrder",
        }),
    }),
    "PurchaseOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "warehouse": "integer",
           "reference": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "warehouse": "warehouse",
           "reference": "reference",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "warehouse": "Warehouse",
            "orderItemList": "OrderItem",
        }),
    }),
    "OrderItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "purchase_order": "integer",
           "purchaseOrder": "integer",
           "sku": "string",
           "quantity": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "purchase_order": "purchase_order",
           "purchaseOrder": "purchase_order",
           "sku": "sku",
           "quantity": "quantity",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "purchase_order": "PurchaseOrder",
           "purchaseOrder": "PurchaseOrder",
        }),
    }),
})