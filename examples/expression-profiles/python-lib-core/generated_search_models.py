from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "DistributionCenter": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "dock_name": "string",
           "dockName": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "dock_name": "dock_name",
           "dockName": "dock_name",
           "version": "version",
        }),
        "relations": MappingProxyType({
            "dispatchOrderList": "DispatchOrder",
        }),
    }),
    "DispatchOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "distribution_center": "integer",
           "distributionCenter": "integer",
           "order_reference": "string",
           "orderReference": "string",
           "handling_note": "string",
           "handlingNote": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "distribution_center": "distribution_center",
           "distributionCenter": "distribution_center",
           "order_reference": "order_reference",
           "orderReference": "order_reference",
           "handling_note": "handling_note",
           "handlingNote": "handling_note",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "distribution_center": "DistributionCenter",
           "distributionCenter": "DistributionCenter",
        }),
    }),
})