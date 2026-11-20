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
            "deliveryOrderList": "DeliveryOrder",
        }),
    }),
    "DeliveryOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "reference": "string",
           "order_date": "date",
           "orderDate": "date",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "reference": "reference",
           "order_date": "order_date",
           "orderDate": "order_date",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
        }),
    }),
})