# teaql-blob-reference

Optional Blob catalog and current-read services for TeaQL Python. Install this wheel alongside the matching `teaql` version. Catalog migration and runtime service installation are explicit host actions; this package does not install schema or expose routes on import.

`SqliteBlobUploadService` offers a host-invoked, scope-bound upload journal. The host must provide current model/action authorization and a trusted parser that consumes every stored byte and returns actual format, size, and SHA256. The service writes through the context's object-storage provider, rechecks the stored generation before confirmation, and promotes the row to `uploaded_unbound` only after full verification. The included PDF verifier in tests is a fixture, not a production format parser. Other SQL backends and production ten-format parsing remain open.

For retention-aware uploads, the host may implement `current_policy_on_lease(actor, lease, target)` on its upload authorization and return an immutable `BlobRetentionPolicy`. The service obtains this trusted policy on the physical SQLite begin lease and snapshots its profile, upload mode and retention durations into the catalog. It rejects direct mode on this server-stream path. Confirmation records `completed_at_ms`; replay never changes the accepted policy or completion time. Older rows remain NULL-policy after migration and are excluded from retention collection. A binding authorization must provide its own current policy on the graph lease; new bindings of unknown-policy rows fail closed. Successful binding preserves the longest accepted unreferenced duration and minimum retention deadline. The final unbind records `last_unbound_at_ms` while the row remains `available`, so its lifetime is measured from the actual final unbind. The shared policy vectors are pinned by SHA-256 in the tests.

`SqliteBlobMaintenanceService` is an optional, explicitly host-scheduled service for expired incomplete uploads and policy-backed completed, unbound server-stream objects. It includes formerly bound objects only after the final unbind deadline and retention floor. Active bindings, unknown-policy legacy rows and direct uploads are excluded. The host supplies a current scope and async `can_maintain` policy, then calls `run_batch(context, cursor)` and may install the service through `BlobReferenceModule(..., maintenance=service)`. Run `catalog.ensure_schema()` as a separate migration before readiness; it adds a unique object-key index and nullable policy/time columns. Cleanup claims rows under SQLite `BEGIN IMMEDIATE`, pins the observed ETag, uses only version-conditional storage deletion, and can resume after a failed final catalog acknowledgment. `FileObjectStorage` guards manifest publication and conditional deletion with a persistent per-key OS file lock. Its ETag includes an immutable generation token, so identical-byte replacement cannot match an older version. A matching delete removes the current data generation and manifest. The host may separately call `FileObjectStorage.sweep_old_generations(key)` for a known object key to remove inaccessible older immutable data generations; it waits for same-key writers and preserves the current manifest generation. Use this only after all processes using that private root run a writer-lock-capable version, and schedule/retry it separately from the catalog receipt. Keep each Blob object key unique and immutable, including across manual S3 writes. Direct-upload quiescence and cross-machine S3 retention remain outside this service.

`SqliteBlobFileGenerationSweepService` supplies a separate, host-scheduled
catalog-driven File sweep. After every process sharing the private File root
has upgraded to the writer-lock protocol, the host constructs it with
`all_writers_upgraded=True` and calls `run_batch(actor, provider, cursor)`
outside graph SQL. It pages only the authorized scope's `server_stream` rows,
including `deleted` rows that may retain inaccessible old data generations.
The provider must be the exact `FileObjectStorage` installed in the current
context. Each outcome reports removed generations or a sanitized failure;
restart the scan from the beginning to retry a failed row. Keep terminal
catalog rows until the File sweep has completed. The host assertion cannot
detect an older external writer on its own; no worker or timer starts at import.

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

For actual DOCX/XLSX parsing, install `teaql-blob-reference[office]` and inject
`teaql_blob_reference.content_office.OfficeBlobContentVerifier`. The office extra
pins python-docx 1.2.0 and openpyxl 3.1.5. The adapter checks every ZIP member
and its CRC under input, decoded-byte and part-count limits, rejects XML entity
declarations, checks the expected
Office main content type and package relationship, then parses the Word body or
every Excel worksheet under an element/cell count limit. It hashes original
bytes and returns the precise Office MIME type. Construction is passive, and
`validate_ready` requires both optional parsers. The in-process parsers do not
provide hard CPU or process-memory isolation. Binary DOC/XLS still need
production adapters.

For actual MP3/MP4 validation on POSIX hosts, inject
`teaql_blob_reference.content_ffmpeg.FfmpegBlobContentVerifier` with absolute
paths to trusted `ffprobe` and `ffmpeg` executables. The host installs and
patches those binaries separately; this wheel does not bundle or fetch them.
`validate_ready` checks availability when the module is activated. The adapter
walks complete MP3 frames or top-level MP4 boxes before forcing the matching
FFmpeg demuxer, probing decoded frame counts and stream properties, and fully
decoding media from a pipe. Client filenames and URLs never reach FFmpeg. It
allows only the `pipe` protocol and bounds input bytes, frame count, video
pixels, concurrent checks, child CPU time and address space, and wall time.
The accepted MP3 profile is MPEG Layer III with fixed, non-free bitrate and a
constant sample rate; MP4 must contain a supported `ftyp` brand, `moov`,
`mdat`, and at least one decodable non-cover-art video stream. The adapter returns the SHA-256
of the original bytes and `audio/mpeg` or `video/mp4`. It is content validation,
not malware scanning; ffprobe/ffmpeg themselves must be kept current.
