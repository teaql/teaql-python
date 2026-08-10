import json
import dataclasses
from enum import Enum
import httpx
from datetime import datetime

from teaql.data_service import (
    DataService,
    QueryRequest,
    QueryResult,
    MutationRequest,
    MutationResult,
    DataServiceCapabilities,
    ExecutionMetadata,
    DataServiceOperation
)
from teaql.core.query import SelectQuery
from teaql.core.mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand
)

class TfpJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        if isinstance(obj, Enum):
            return obj.name
        return super().default(obj)

class TfpHttpProvider(DataService):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(base_url=self.base_url)

    def capabilities(self) -> DataServiceCapabilities:
        return DataServiceCapabilities(
            query=True,
            mutation=True,
            transaction=False,
            schema=False,
            id_generation=False
        )

    async def query(self, ctx, request: QueryRequest) -> QueryResult:
        start_time = datetime.now()
        payload = json.dumps(request.query, cls=TfpJsonEncoder)
        
        response = await self.client.post('/query', content=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        
        data = response.json()
        end_time = datetime.now()
        
        metadata = ExecutionMetadata(
            backend="TfpHttpProvider",
            operation=DataServiceOperation.Query,
            started_at=start_time,
            ended_at=end_time,
            result_count=len(data.get("data", []))
        )
        
        return QueryResult(
            rows=data.get("data", []),
            facets=data.get("facets", {}),
            metadata=metadata
        )

    async def mutate(self, ctx, request: MutationRequest) -> MutationResult:
        start_time = datetime.now()
        cmd = request.cmd
        
        # Determine action and entity
        if isinstance(cmd, InsertCommand):
            action = "Create"
            entity = cmd.entity
            values = cmd.values
            cmd_id = None
        elif isinstance(cmd, UpdateCommand):
            action = "Update"
            entity = cmd.entity
            values = cmd.values
            cmd_id = cmd.id
        elif isinstance(cmd, DeleteCommand):
            action = "Delete"
            entity = cmd.entity
            values = {}
            cmd_id = cmd.id
        elif isinstance(cmd, RecoverCommand):
            action = "Recover"
            entity = cmd.entity
            values = {}
            cmd_id = cmd.id
        else:
            raise ValueError(f"Unknown mutation command: {type(cmd)}")

        payload_dict = {
            "entity": entity,
            "action": action,
            "payload": values,
            "id": cmd_id
        }
        
        payload_str = json.dumps(payload_dict, cls=TfpJsonEncoder)
        
        response = await self.client.post('/mutate', content=payload_str, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        
        data = response.json()
        end_time = datetime.now()
        
        metadata = ExecutionMetadata(
            backend="TfpHttpProvider",
            operation=DataServiceOperation.Mutation,
            started_at=start_time,
            ended_at=end_time,
            affected_rows=data.get("affectedRows", 0)
        )
        
        gen_values = {}
        if data.get("data") and len(data["data"]) > 0:
            gen_values = data["data"][0]
            
        return MutationResult(
            affected_rows=data.get("affectedRows", 0),
            generated_values=gen_values,
            metadata=metadata
        )
