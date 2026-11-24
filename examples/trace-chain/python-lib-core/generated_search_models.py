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
            "customerOrderList": "CustomerOrder",
        }),
    }),
    "CustomerOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "order_number": "string",
           "orderNumber": "string",
           "description": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "order_number": "order_number",
           "orderNumber": "order_number",
           "description": "description",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
            "orderItemList": "OrderItem",
            "paymentList": "Payment",
            "shipmentList": "Shipment",
        }),
    }),
    "OrderItem": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer_order": "integer",
           "customerOrder": "integer",
           "name": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer_order": "customer_order",
           "customerOrder": "customer_order",
           "name": "name",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer_order": "CustomerOrder",
           "customerOrder": "CustomerOrder",
        }),
    }),
    "Payment": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer_order": "integer",
           "customerOrder": "integer",
           "reference_code": "string",
           "referenceCode": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer_order": "customer_order",
           "customerOrder": "customer_order",
           "reference_code": "reference_code",
           "referenceCode": "reference_code",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer_order": "CustomerOrder",
           "customerOrder": "CustomerOrder",
            "paymentAttemptList": "PaymentAttempt",
        }),
    }),
    "PaymentAttempt": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "payment": "integer",
           "reference_code": "string",
           "referenceCode": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "payment": "payment",
           "reference_code": "reference_code",
           "referenceCode": "reference_code",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "payment": "Payment",
        }),
    }),
    "Shipment": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer_order": "integer",
           "customerOrder": "integer",
           "reference_code": "string",
           "referenceCode": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer_order": "customer_order",
           "customerOrder": "customer_order",
           "reference_code": "reference_code",
           "referenceCode": "reference_code",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer_order": "CustomerOrder",
           "customerOrder": "CustomerOrder",
        }),
    }),
})