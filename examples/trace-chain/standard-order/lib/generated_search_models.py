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
            "orderStatusList": "OrderStatus",
            "customerList": "Customer",
        }),
    }),
    "OrderStatus": MappingProxyType({
        "fields": MappingProxyType({
           "platform": "integer",
           "id": "integer",
           "name": "string",
           "code": "string",
           "color": "string",
           "display_order": "integer",
           "displayOrder": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "platform": "platform",
           "id": "id",
           "name": "name",
           "code": "code",
           "color": "color",
           "display_order": "display_order",
           "displayOrder": "display_order",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
            "customerOrderList": "CustomerOrder",
        }),
    }),
    "Customer": MappingProxyType({
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
            "customerOrderList": "CustomerOrder",
        }),
    }),
    "CustomerOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer": "integer",
           "status": "integer",
           "order_number": "string",
           "orderNumber": "string",
           "order_date": "date",
           "orderDate": "date",
           "total_amount": "decimal",
           "totalAmount": "decimal",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer": "customer",
           "status": "status",
           "order_number": "order_number",
           "orderNumber": "order_number",
           "order_date": "order_date",
           "orderDate": "order_date",
           "total_amount": "total_amount",
           "totalAmount": "total_amount",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer": "Customer",
           "status": "OrderStatus",
            "orderItemList": "OrderItem",
        }),
    }),
    "OrderItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer_order": "integer",
           "customerOrder": "integer",
           "product_name": "string",
           "productName": "string",
           "quantity": "integer",
           "unit_price": "decimal",
           "unitPrice": "decimal",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer_order": "customer_order",
           "customerOrder": "customer_order",
           "product_name": "product_name",
           "productName": "product_name",
           "quantity": "quantity",
           "unit_price": "unit_price",
           "unitPrice": "unit_price",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer_order": "CustomerOrder",
           "customerOrder": "CustomerOrder",
        }),
    }),
})