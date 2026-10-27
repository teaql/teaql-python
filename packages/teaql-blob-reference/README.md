# teaql-blob-reference

Optional Blob catalog and current-read services for TeaQL Python. Install this wheel alongside the matching `teaql` version. Catalog migration and runtime service installation are explicit host actions; this package does not install schema or expose routes on import.

`SqliteBlobUploadService` offers a host-invoked, scope-bound upload journal. The host must provide current model/action authorization and a trusted parser that consumes every stored byte and returns actual format, size, and SHA256. The service writes through the context's object-storage provider, rechecks the stored generation before confirmation, and promotes the row to `uploaded_unbound` only after full verification. The included PDF verifier in tests is a fixture, not a production format parser. Failure recovery, retention/GC, other SQL backends, and production ten-format parsing remain open.
