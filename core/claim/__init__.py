"""
Claim layer package for ClaimShield AI.
"""
from core.claim.models import Claim, EvidenceItem
from core.claim.consistency import (
    check_date_consistency,
    check_amount_consistency,
    verify_claim_consistency,
)

from core.claim.cross_evidence import (
    verify_cross_evidence,
    check_identifier_consistency,
    check_cross_evidence_dates_and_amounts,
    compute_image_text_similarity,
    RelationshipStatus,
)

from core.claim.adapter import (
    document_to_evidence_item,
    document_file_to_evidence_item,
    resolve_document_date,
    resolve_document_amount,
    analyze_claim,
)

__all__ = [
    "Claim",
    "EvidenceItem",
    "check_date_consistency",
    "check_amount_consistency",
    "verify_claim_consistency",
    "verify_cross_evidence",
    "check_identifier_consistency",
    "check_cross_evidence_dates_and_amounts",
    "compute_image_text_similarity",
    "RelationshipStatus",
    "document_to_evidence_item",
    "document_file_to_evidence_item",
    "resolve_document_date",
    "resolve_document_amount",
    "analyze_claim",
]

