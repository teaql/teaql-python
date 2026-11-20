from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "DistributionCenter": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "Id": "integer",
           "dock_name": "string",
           "dockName": "string",
           "DockName": "string",
           "version": "integer",
           "Version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "Id": "id",
           "dock_name": "dock_name",
           "dockName": "dock_name",
           "DockName": "dock_name",
           "version": "version",
           "Version": "version",
        }),
        "relations": MappingProxyType({
            "dispatchOrderList": "DispatchOrder",
        }),
    }),
    "DispatchOrder": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "Id": "integer",
           "distribution_center": "integer",
           "distributionCenter": "integer",
           "DistributionCenter": "integer",
           "order_reference": "string",
           "orderReference": "string",
           "OrderReference": "string",
           "handling_note": "string",
           "handlingNote": "string",
           "HandlingNote": "string",
           "version": "integer",
           "Version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "Id": "id",
           "distribution_center": "distribution_center",
           "distributionCenter": "distribution_center",
           "DistributionCenter": "distribution_center",
           "order_reference": "order_reference",
           "orderReference": "order_reference",
           "OrderReference": "order_reference",
           "handling_note": "handling_note",
           "handlingNote": "handling_note",
           "HandlingNote": "handling_note",
           "version": "version",
           "Version": "version",
        }),
        "relations": MappingProxyType({
           "distribution_center": "DistributionCenter",
           "distributionCenter": "DistributionCenter",
           "DistributionCenter": "DistributionCenter",
        }),
    }),
})