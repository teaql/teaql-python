"""Optional secure-document reference services; no base runtime reverse dependency."""

from .round_trip_reference import (
    ContextBoundReferenceRuntime, ReferenceDocumentScope, ReferenceIdentity,
    ReferenceKey, RoundTripReferenceError, StaticReferenceKeyProvider,
    TrustedReferencePrincipal, VerifiedEntityReference,
)
from .document_round_trip import (
    BlobSelectionClaim, BlobSelectionTarget, BoundDocumentSnapshot,
    DocumentBlobBindingSnapshot, DocumentEntitySnapshot, DocumentRelationSnapshot,
    DocumentSnapshot, PreparedBoundDocument, SecureDocumentAssembly,
    SecureDocumentReferenceModule, VerifiedDocument,
)
from .sqlite_document_service import (
    AcceptedDocument, ContextualDocument, CurrentBoundDocument,
    DocumentBlobSelectionSubmission, DocumentBlobSelectionClaim, DocumentCommandReceipt,
    VerifiedDocumentBlobSelection, SQLiteContextBoundDocumentService,
    SQLiteDocumentCommandJournal, SubmittedDocumentCommand,
)

__all__ = [
    "ContextBoundReferenceRuntime", "ReferenceDocumentScope", "ReferenceIdentity",
    "ReferenceKey", "RoundTripReferenceError", "StaticReferenceKeyProvider",
    "TrustedReferencePrincipal", "VerifiedEntityReference",
    "BlobSelectionClaim", "BlobSelectionTarget", "BoundDocumentSnapshot",
    "DocumentBlobBindingSnapshot", "DocumentEntitySnapshot", "DocumentRelationSnapshot",
    "DocumentSnapshot", "PreparedBoundDocument", "SecureDocumentAssembly",
    "SecureDocumentReferenceModule", "VerifiedDocument",
    "AcceptedDocument", "ContextualDocument", "CurrentBoundDocument",
    "DocumentBlobSelectionSubmission", "DocumentBlobSelectionClaim", "DocumentCommandReceipt",
    "VerifiedDocumentBlobSelection", "SQLiteContextBoundDocumentService",
    "SQLiteDocumentCommandJournal", "SubmittedDocumentCommand",
]
