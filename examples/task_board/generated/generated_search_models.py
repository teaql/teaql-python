from types import MappingProxyType

# Generated trusted field/type metadata. Runtime owns parsing, binding and warnings.
GENERATED_SEARCH_MODELS = MappingProxyType({
    "Platform": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "name": "string",
           "founded": "timestamp",
           "user_email": "string",
           "userEmail": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "name": "name",
           "founded": "founded",
           "user_email": "user_email",
           "userEmail": "user_email",
           "version": "version",
        }),
        "relations": MappingProxyType({
            "taskStatusList": "TaskStatus",
            "taskList": "Task",
        }),
    }),
    "TaskStatus": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "name": "string",
           "code": "string",
           "color": "string",
           "display_order": "decimal",
           "displayOrder": "decimal",
           "progress": "decimal",
           "platform": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "name": "name",
           "code": "code",
           "color": "color",
           "display_order": "display_order",
           "displayOrder": "display_order",
           "progress": "progress",
           "platform": "platform",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "platform": "Platform",
            "taskList": "Task",
        }),
    }),
    "Task": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "name": "string",
           "status": "integer",
           "platform": "integer",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "name": "name",
           "status": "status",
           "platform": "platform",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "status": "TaskStatus",
           "platform": "Platform",
            "taskExecutionLogList": "TaskExecutionLog",
        }),
    }),
    "TaskExecutionLog": MappingProxyType({
        "fields": MappingProxyType({
           "id": "integer",
           "task": "integer",
           "action": "string",
           "detail": "string",
           "version": "integer",
        }),
        "query_fields": MappingProxyType({
           "id": "id",
           "task": "task",
           "action": "action",
           "detail": "detail",
           "version": "version",
        }),
        "relations": MappingProxyType({
           "task": "Task",
        }),
    }),
})