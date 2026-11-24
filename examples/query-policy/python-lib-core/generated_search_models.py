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
            "tenantList": "Tenant",
        }),
    }),
    "Tenant": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "name": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "name": "name",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
            "purchaseOrderList": "PurchaseOrder",
            "orderItemList": "OrderItem",
        }),
    }),
    "PurchaseOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "tenant": "integer",
           "reference": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "tenant": "tenant",
           "reference": "reference",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "tenant": "Tenant",
            "orderItemList": "OrderItem",
        }),
    }),
    "OrderItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "purchase_order": "integer",
           "purchaseOrder": "integer",
           "tenant": "integer",
           "sku": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "purchase_order": "purchase_order",
           "purchaseOrder": "purchase_order",
           "tenant": "tenant",
           "sku": "sku",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "purchase_order": "PurchaseOrder",
           "purchaseOrder": "PurchaseOrder",
           "tenant": "Tenant",
        }),
    }),
})