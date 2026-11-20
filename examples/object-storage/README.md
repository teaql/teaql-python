# Context owned object storage

Tracking: [Python #52](https://github.com/teaql/teaql-python/issues/52),
[shared contract #122](https://github.com/teaql/teaql-conformance/issues/122).


## File an order receipt

`model.xml` defines the commerce platform, order and attachment. The
`python-app-console` uses the generated domain model and installs the S3 provider
in trusted Context setup. It uploads a receipt, saves the order association
with generated mutations, then uses generated Q and E to recover the
reference and check the downloaded bytes, content type and SHA-256.

Run `bash examples/object-storage/verify.sh` with the dedicated fixture settings
below. The script preserves the provider and lifecycle checks and runs the
order scenario twice against one SQLite file. A create-only conflict and a
too-small read limit leave the receipt intact. After the example removes its
own test object, a fresh get reports missing while the order association
remains available. Downloaded fixture bytes, SQLite and compact logs stay in
the evidence directory. Set `TEAQL_ORDER_ATTACHMENT_EVIDENCE_DIR` to select a
fresh output path.

## Provider setup

Install this checkout with `python -m pip install -e '.[object-storage-s3]'`.
The optional boto3 provider owns signing, credentials and the shared HTTP pool.
SDK types stay outside the core contract. The application installs the provider
at trusted startup and closes it at shutdown.

```python
from teaql.core.object_storage import ObjectKey, PutOptions, WriteMode
from teaql.provider.s3 import S3ObjectStorage
from teaql.runtime import UserContext

provider = S3ObjectStorage.connect("attachments")  # SDK default credentials chain
context = UserContext().with_object_storage(provider)
storage = context.object_storage("store payment receipt attachment")
key = ObjectKey("receipts/opaque-reference.pdf")
storage.put(key, source, PutOptions(content_length, WriteMode.CREATE_ONLY))
link = storage.get_read_url(key)
with storage.get(key) as response:
    block = response.stream.read(65536)
```

This binary-stream API is synchronous, matching boto3 and Python BinaryIO.
Async services can run the complete operation with `asyncio.to_thread`; never
close the input while that worker is still running. Uploads stage in a private
temporary file with bounded buffers, exact length checks and a 5 GiB limit.
The facade closes upload inputs. Downloads stream and require explicit close;
`get_bytes(key, maximum_bytes)` enforces an explicit memory ceiling.

Create-only uses atomic conditional PUT; replacement is explicit. Only confirmed
object absence becomes false. Missing buckets, permissions and network failures
remain typed errors. Keys and default five-minute URLs have different lifetimes;
the URL is a reusable bearer link, can expire early with credentials, and does
not check existence or infer business permission. Diagnostic representations
and operation events exclude keys, body, metadata, URLs and SDK error messages.
Object storage is independent of SQL transactions.

Set the four `TEAQL_S3_ENDPOINT`, `TEAQL_S3_BUCKET`, `TEAQL_S3_ACCESS_KEY`,
`TEAQL_S3_SECRET_KEY` variables to a dedicated test service, then run twice:

```bash
bash examples/object-storage/verify.sh
bash examples/object-storage/verify.sh
```

The example uses the repository source via PYTHONPATH, provisions its test bucket
if absent and deletes only its unique keys. The production provider never
creates buckets. Use `PYTHON=/path/to/venv/bin/python` to select an environment
with boto3 and pytest. A local fixture pass qualifies that fixture, not every
S3-compatible service. Range/list/copy/multipart and signed upload are extensions.
