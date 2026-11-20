"""File an order receipt and retrieve it through the saved attachment."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import boto3
from botocore.config import Config
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.object_storage import ObjectKey, PutOptions, StorageErrorCode, WriteMode
from teaql.data_service import SQLiteTeaQLClient
from teaql.provider.s3 import S3ObjectStorage
from teaql.runtime import UserContext

from .s3_lifecycle import expect


RECEIPT = b"TeaQL order receipt fixture\nItem: tea\nTotal: 12.50\n"
FILENAME = "receipt.txt"
MEDIA_TYPE = "text/plain"


class SafeAudit:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, _context, event):
        self.events.append(event)


async def main(database, download, round_number):
    client = boto3.client("s3", endpoint_url=os.environ["TEAQL_S3_ENDPOINT"], region_name="us-east-1",
        aws_access_key_id=os.environ["TEAQL_S3_ACCESS_KEY"], aws_secret_access_key=os.environ["TEAQL_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 1}, s3={"addressing_style": "path"}))
    provider = S3ObjectStorage(client, os.environ["TEAQL_S3_BUCKET"])
    sqlite = SQLiteTeaQLClient(str(database))
    audit = SafeAudit()
    observations = []
    trace = f"order-attachment-{round_number}"
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
        .insert_resource("dataService", sqlite)
        .with_trace_id(trace)
        .with_object_storage(provider)
        .with_object_storage_observer(observations.append)
        .initialize_audit(None, audit))
    storage = context.object_storage("file and retrieve an order receipt")
    key_text = f"private-order-attachments/{uuid4().hex}"
    key = ObjectKey(key_text)
    digest = hashlib.sha256(RECEIPT).hexdigest()
    try:
        await context.ensure_schema()
        platform = await (Q.commerce_platforms().with_id_is(1).limit(1)
            .comment("load the commerce platform").purpose("associate the new order to its root")
            .execute_for_one(context))
        assert platform is not None
        order_number = f"ATTACH-ORDER-{round_number}"
        order = await (Q.customer_orders().comment("prepare receipt order")
            .purpose("file a receipt against this order").new_entity(context))
        order.update_order_number(order_number).update_commerce_platform(platform.id)
        await order.audit_as("place the order receiving the receipt").save(context)

        assert not storage.exists(key)
        options = PutOptions(len(RECEIPT), WriteMode.CREATE_ONLY, MEDIA_TYPE, {"receipt-sha256": digest})
        storage.put_bytes(key, RECEIPT, options)
        attachment = await (Q.order_attachments().comment("prepare receipt attachment")
            .purpose("save the uploaded receipt reference on its order").new_entity(context))
        attachment.update_customer_order(order.id).update_file_name(FILENAME).update_content_type(MEDIA_TYPE)
        attachment.update_content_length(len(RECEIPT)).update_content_sha256(digest).update_object_key(key_text)
        await attachment.audit_as("associate the stored receipt with its order").save(context)

        async def attachments():
            return await (Q.order_attachments().filter_by_customer_order(order.id).limit(2)
                .comment("load order attachments").purpose("retrieve this order's stored receipt")
                .execute_for_list(context))

        loaded, = await attachments()
        receipt = E.order_attachment(loaded)
        assert receipt.id().eval() == attachment.id and receipt.customer_order_id().eval() == order.id
        assert receipt.file_name().eval() == FILENAME and receipt.content_type().eval() == MEDIA_TYPE
        persisted_key = ObjectKey(receipt.object_key().eval())
        length = receipt.content_length().eval()
        assert length == len(RECEIPT) and persisted_key == key
        metadata = storage.head(persisted_key)
        assert metadata.size == length and metadata.content_type == MEDIA_TYPE
        assert metadata.custom_metadata["receipt-sha256"] == receipt.content_sha256().eval()
        expect(StorageErrorCode.CONFLICT,
               lambda: storage.put_bytes(persisted_key, b"replacement", PutOptions(11, WriteMode.CREATE_ONLY)))
        expect(StorageErrorCode.TOO_LARGE, lambda: storage.get_bytes(persisted_key, length - 1))
        returned = storage.get_bytes(persisted_key, length)
        assert returned == RECEIPT and hashlib.sha256(returned).hexdigest() == receipt.content_sha256().eval() == digest
        download.write_bytes(returned)

        storage.delete(persisted_key)
        expect(StorageErrorCode.NOT_FOUND, lambda: storage.get(persisted_key))
        assert not storage.exists(persisted_key)
        assert [row.id for row in await attachments()] == [attachment.id]
        assert observations and all(event.trace_id == trace for event in observations)
        assert key_text not in repr(observations)
        events = [event for event in audit.events if event.entity in {"CustomerOrder", "OrderAttachment"}]
        assert [event.entity for event in events] == ["CustomerOrder", "OrderAttachment"]
        assert key_text not in repr(events)
        print("ORDER_ATTACHMENT " + json.dumps(dict(round=round_number, order=order.id, attachment=attachment.id,
            orderNumber=order_number, filename=FILENAME, contentType=MEDIA_TYPE, length=length, sha256=digest,
            conflict=True, sizeRefused=True, missing=True, businessAudits=len(events)), sort_keys=True))
    finally:
        try:
            storage.delete(key)
        finally:
            provider.close()
            await sqlite.close()


if __name__ == "__main__":
    db, output, round_argument = sys.argv[1:]
    asyncio.run(main(Path(db), Path(output), int(round_argument)))
