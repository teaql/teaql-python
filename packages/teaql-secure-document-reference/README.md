# TeaQL secure document reference

Optional secure reference protocol and document governance package. The base `teaql` runtime does not import it. Installation, key policy and host authorization remain explicit.

The current source implements governed tqr1 entity references, tqd1/tqd2 document snapshots, and tqs1 Blob selections with the shared Java/Rust wire vectors. `SecureDocumentReferenceModule.install` passively attaches a trusted snapshot contributor to the runtime's governed view preparation. Full document open/accept/replay, transactional selection consumption, and release gates remain in progress.
