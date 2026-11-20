from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "CommercePlatform": MappingProxyType({
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
           "order_number": "string",
           "orderNumber": "string",
           "commerce_platform": "integer",
           "commercePlatform": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "order_number": "order_number",
           "orderNumber": "order_number",
           "commerce_platform": "commerce_platform",
           "commercePlatform": "commerce_platform",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "commerce_platform": "CommercePlatform",
           "commercePlatform": "CommercePlatform",
            "orderAttachmentList": "OrderAttachment",
        }),
    }),
    "OrderAttachment": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "customer_order": "integer",
           "customerOrder": "integer",
           "file_name": "string",
           "fileName": "string",
           "content_type": "string",
           "contentType": "string",
           "content_length": "integer",
           "contentLength": "integer",
           "content_sha256": "string",
           "contentSha256": "string",
           "object_key": "string",
           "objectKey": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "customer_order": "customer_order",
           "customerOrder": "customer_order",
           "file_name": "file_name",
           "fileName": "file_name",
           "content_type": "content_type",
           "contentType": "content_type",
           "content_length": "content_length",
           "contentLength": "content_length",
           "content_sha256": "content_sha256",
           "contentSha256": "content_sha256",
           "object_key": "object_key",
           "objectKey": "object_key",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "customer_order": "CustomerOrder",
           "customerOrder": "CustomerOrder",
        }),
    }),
})