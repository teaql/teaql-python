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
            "freightQuoteList": "FreightQuote",
        }),
    }),
    "FreightQuote": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "platform": "integer",
           "reference": "string",
           "amount": "decimal",
           "shipment_number": "integer",
           "shipmentNumber": "integer",
           "package_count": "integer",
           "packageCount": "integer",
           "delivery_date": "date",
           "deliveryDate": "date",
           "pickup_time": "unsupported",
           "pickupTime": "unsupported",
           "quoted_at": "timestamp",
           "quotedAt": "timestamp",
           "instructions": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "platform": "platform",
           "reference": "reference",
           "amount": "amount",
           "shipment_number": "shipment_number",
           "shipmentNumber": "shipment_number",
           "package_count": "package_count",
           "packageCount": "package_count",
           "delivery_date": "delivery_date",
           "deliveryDate": "delivery_date",
           "pickup_time": "pickup_time",
           "pickupTime": "pickup_time",
           "quoted_at": "quoted_at",
           "quotedAt": "quoted_at",
           "instructions": "instructions",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
        }),
    }),
})