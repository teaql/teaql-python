# teaql-blob-reference

Optional Blob catalog and current-read services for TeaQL Python. Install this wheel alongside the matching `teaql` version. Catalog migration and runtime service installation are explicit host actions; this package does not install schema or expose routes on import.

`SqliteBlobUploadService` offers a host-invoked, scope-bound upload journal. The host must provide current model/action authorization and a trusted parser that consumes every stored byte and returns actual format, size, and SHA256. The service writes through the context's object-storage provider, rechecks the stored generation before confirmation, and promotes the row to `uploaded_unbound` only after full verification. The included PDF verifier in tests is a fixture, not a production format parser. Other SQL backends and production ten-format parsing remain open.

For retention-aware uploads, the host may implement `current_policy_on_lease(actor, lease, target)` on its upload authorization and return an immutable `BlobRetentionPolicy`. The service obtains this trusted policy on the physical SQLite begin lease and snapshots its profile, upload mode and retention durations into the catalog. It rejects direct mode on this server-stream path. Confirmation records `completed_at_ms`; replay never changes the accepted policy or completion time. Older rows remain NULL-policy after migration and are excluded from retention collection. A binding authorization must provide its own current policy on the graph lease; new bindings of unknown-policy rows fail closed. Successful binding preserves the longest accepted unreferenced duration and minimum retention deadline. The final unbind records `last_unbound_at_ms` while the row remains `available`, so its lifetime is measured from the actual final unbind. The shared policy vectors are pinned by SHA-256 in the tests.

`SqliteBlobMaintenanceService` is an optional, explicitly host-scheduled service for expired incomplete uploads and policy-backed completed, unbound server-stream objects. It includes formerly bound objects only after the final unbind deadline and retention floor. Active bindings, unknown-policy legacy rows and direct uploads are excluded. The host supplies a current scope and async `can_maintain` policy, then calls `run_batch(context, cursor)` and may install the service through `BlobReferenceModule(..., maintenance=service)`. Run `catalog.ensure_schema()` as a separate migration before readiness; it adds a unique object-key index and nullable policy/time columns. Cleanup claims rows under SQLite `BEGIN IMMEDIATE`, pins the observed ETag, uses only version-conditional storage deletion, and can resume after a failed final catalog acknowledgment. `FileObjectStorage` guards manifest publication and conditional deletion with a persistent per-key OS file lock. Its ETag includes an immutable generation token, so identical-byte replacement cannot match an older version. A matching delete removes the current data generation and manifest; older immutable generations remain for a separate collector. Keep each Blob object key unique and immutable, including across manual S3 writes. Direct-upload quiescence, older File generations and cross-machine S3 retention remain outside this service.

For actual JPEG/PNG parsing, install `teaql-blob-reference[image]` and inject
`teaql_blob_reference.content_pillow.PillowBlobContentVerifier`. The image extra
pins Pillow 12.3.0, the newest release supporting Python 3.10 at this checkpoint.
The adapter validates complete JPEG/PNG containers and PNG CRCs, checks the
decoder's real format and loads all pixels with explicit input, pixel and
concurrent-work bounds. It has no hard CPU/process isolation. Construction is
passive; `BlobReferenceModule.ready` invokes its optional decoder readiness check.
It accepts `jpg`, `jpeg` and `png` only. The other formats need separate
production adapters; the earlier PDF fixture test does not establish them.

For actual PDF parsing, install `teaql-blob-reference[pdf]` and inject
`teaql_blob_reference.content_pypdf.PypdfBlobContentVerifier`. The PDF extra
pins pypdf 6.21.3. This adapter checks a complete PDF container with strict
cross-reference parsing, a real page tree and content operators, and bounded
input, pages, decoded page content and concurrent work. It rejects encrypted
PDFs. This is parser validation, not malware scanning or hard CPU/process
isolation. The PDF fixture verifier used in older S3 tests remains test-only.
