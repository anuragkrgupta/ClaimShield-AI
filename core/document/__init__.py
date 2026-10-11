"""
Document analysis module for ClaimShield AI.
Exposes extraction, tampering detection, and document authenticity checks.
"""
from core.document.extractor import (
    DocumentMetadata,
    ExtractedDocument,
    extract_document,
)
from core.document.tampering import (
    check_document_tampering,
    check_document_authenticity,
)

__all__ = [
    "DocumentMetadata",
    "ExtractedDocument",
    "extract_document",
    "check_document_tampering",
    "check_document_authenticity",
]
