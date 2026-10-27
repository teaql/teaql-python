# teaql-blob-reference

Optional Blob catalog and current-read services for TeaQL Python. Install this wheel alongside the matching `teaql` version. Catalog migration and runtime service installation are explicit host actions; this package does not install schema or expose routes on import.

`SqliteBlobUploadService` offers a host-invoked, scope-bound upload journal. The host must provide current model/action authorization and a trusted parser that consumes every stored byte and returns actual format, size, and SHA256. The service writes through the context's object-storage provider, rechecks the stored generation before confirmation, and promotes the row to `uploaded_unbound` only after full verification. The included PDF verifier in tests is a fixture, not a production format parser. Failure recovery, retention/GC, other SQL backends, and production ten-format parsing remain open.

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
