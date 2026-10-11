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
]

