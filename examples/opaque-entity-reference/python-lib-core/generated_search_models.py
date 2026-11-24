from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "Merchant": MappingProxyType({
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
            "salesOrderList": "SalesOrder",
        }),
    }),
    "SalesOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "merchant": "integer",
           "order_number": "string",
           "orderNumber": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "merchant": "merchant",
           "order_number": "order_number",
           "orderNumber": "order_number",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "merchant": "Merchant",
            "orderItemList": "OrderItem",
        }),
    }),
    "OrderItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "sales_order": "integer",
           "salesOrder": "integer",
           "sku": "string",
           "quantity": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "sales_order": "sales_order",
           "salesOrder": "sales_order",
           "sku": "sku",
           "quantity": "quantity",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "sales_order": "SalesOrder",
           "salesOrder": "SalesOrder",
        }),
    }),
})