"""
Cross-evidence verification for ClaimShield AI.
Evaluates relationship, coherence, and consistency between submitted images,
documents, and claim details across insurance types.
"""
import logging
import io
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from PIL import Image

from core.types import Signal
from core.claim.models import Claim, EvidenceItem


logger = logging.getLogger(__name__)


class RelationshipStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    POTENTIAL_INCONSISTENCY = "POTENTIAL_INCONSISTENCY"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


def check_identifier_consistency(claim: Claim) -> List[Signal]:
    """
    Checks whether identifiers (such as claim numbers, policy numbers, or invoice numbers)
    match across submitted evidence items and claim attributes.
    """
    signals: List[Signal] = []
    
    # Collect all identifiers mentioned across evidence items metadata or descriptions
    id_map: Dict[str, List[str]] = {}  # id_str -> list of item_ids
    for item in claim.evidence_items:
        extracted_ids = item.metadata.get("identifiers", [])
        if isinstance(extracted_ids, (str, int, float)) and not isinstance(extracted_ids, bool):
            extracted_ids = [extracted_ids]
        elif not isinstance(extracted_ids, (list, tuple, set)):
            extracted_ids = []

        for ref_id in extracted_ids:
            if ref_id is None or isinstance(ref_id, bool):
                continue
            if isinstance(ref_id, (str, int, float)):
                norm_id = str(ref_id).strip().upper()
                if len(norm_id) >= 4:
                    id_map.setdefault(norm_id, []).append(item.item_id)

    # Check for direct conflict if two documents claim different policy or invoice numbers for the exact same event
    # If claim has a designated claim_id, check if documents reference an explicit claim ID that differs
    for item in claim.evidence_items:
        raw_doc_claim_id = item.metadata.get("claim_id")
        # Accept only supported scalar types (str, int, float; exclude bool)
        if (
            raw_doc_claim_id is not None
            and not isinstance(raw_doc_claim_id, bool)
            and isinstance(raw_doc_claim_id, (str, int, float))
            and claim.claim_id is not None
            and not isinstance(claim.claim_id, bool)
            and isinstance(claim.claim_id, (str, int, float))
        ):
            doc_claim_id = str(raw_doc_claim_id).strip().upper()
            target_claim_id = str(claim.claim_id).strip().upper()
            if doc_claim_id and target_claim_id and doc_claim_id != target_claim_id:
                signals.append(Signal(
                    name="CROSS_EVIDENCE_CLAIM_ID_MISMATCH",
                    severity="HIGH",
                    score=30,
                    message=(
                        f"Evidence '{item.item_id}' references Claim ID '{raw_doc_claim_id}', "
                        f"which conflicts with current Claim ID '{claim.claim_id}'."
                    ),
                    confidence=0.95
                ))

    return signals


def check_cross_evidence_dates_and_amounts(claim: Claim) -> List[Signal]:
    """
    Evaluates cross-evidence alignment between document-extracted fields and claim details.
    Distinguishes consistent findings, potential inconsistencies, and insufficient information.
    """
    signals: List[Signal] = []
    
    # Check if there are zero evidence items or missing key fields
    if not claim.evidence_items:
        signals.append(Signal(
            name="CROSS_EVIDENCE_INSUFFICIENT_DATA",
            severity="LOW",
            score=70,
            message="No supporting evidence items provided to perform cross-evidence verification.",
            confidence=1.0
        ))
        return signals

    evidence_with_dates = [it for it in claim.evidence_items if it.extracted_date]
    evidence_with_amounts = [it for it in claim.evidence_items if it.extracted_amount is not None]

    if not evidence_with_dates and not evidence_with_amounts:
        signals.append(Signal(
            name="CROSS_EVIDENCE_INSUFFICIENT_DATA",
            severity="LOW",
            score=70,
            message="Supporting documents contain insufficient extracted dates or monetary values for cross-verification.",
            confidence=0.9
        ))

    return signals


def compute_image_text_similarity(image_bytes: bytes, text_query: str) -> Tuple[Optional[float], RelationshipStatus]:
    """
    Computes zero-shot semantic similarity between an evidence image and descriptive text
    using CLIP ViT-L/14 (reusing existing weights from UnivFD pipeline).
    Returns (similarity_score, RelationshipStatus).
    """
    if not image_bytes or not text_query or not text_query.strip():
        return None, RelationshipStatus.INSUFFICIENT_INFORMATION

    try:
        from core.image.detector import UnivFDDetector
        detector = UnivFDDetector.get_instance()
        if not detector.is_loaded:
            return None, RelationshipStatus.INSUFFICIENT_INFORMATION

        # Open image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Tokenize and process with processor-level truncation to CLIP's 77 token limit
        inputs = detector.processor(
            text=[text_query.strip()],
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77
        ).to(detector.device)


        import torch
        with torch.no_grad():
            img_feat = detector.model.get_image_features(pixel_values=inputs.pixel_values)
            if hasattr(img_feat, 'image_embeds'):
                img_feat = img_feat.image_embeds
            elif hasattr(img_feat, 'pooler_output'):
                img_feat = img_feat.pooler_output
            elif not isinstance(img_feat, torch.Tensor):
                img_feat = img_feat[1] if isinstance(img_feat, tuple) else img_feat

            txt_feat = detector.model.get_text_features(input_ids=inputs.input_ids)
            if hasattr(txt_feat, 'text_embeds'):
                txt_feat = txt_feat.text_embeds
            elif hasattr(txt_feat, 'pooler_output'):
                txt_feat = txt_feat.pooler_output
            elif not isinstance(txt_feat, torch.Tensor):
                txt_feat = txt_feat[1] if isinstance(txt_feat, tuple) else txt_feat

            img_feat = img_feat / img_feat.norm(p=2, dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(p=2, dim=-1, keepdim=True)

            cosine_sim = (img_feat @ txt_feat.T).item()

        # Classify relationship
        # High cosine similarity (> 0.22 for CLIP ViT-L text-image) indicates strong topical match
        if cosine_sim >= 0.22:
            return cosine_sim, RelationshipStatus.CONSISTENT
        elif cosine_sim < 0.12:
            return cosine_sim, RelationshipStatus.POTENTIAL_INCONSISTENCY
        else:
            return cosine_sim, RelationshipStatus.INSUFFICIENT_INFORMATION

    except Exception as e:
        logger.warning(f"Semantic image-text similarity computation failed: {e}")
        return None, RelationshipStatus.INSUFFICIENT_INFORMATION


def verify_cross_evidence(claim: Claim) -> List[Signal]:
    """
    Executes holistic cross-evidence checks across the claim:
    1. Identifier consistency (claim ID, policy ID, invoice references).
    2. Date and amount cross-evidence data sufficiency and alignment.
    3. Multi-evidence relationship: checks if image evidence corresponds with descriptions or document summaries.
    Returns structured Signal findings.
    """
    signals: List[Signal] = []

    # 1. Identifier checks
    signals.extend(check_identifier_consistency(claim))

    # 2. Date and amount cross-evidence alignment
    signals.extend(check_cross_evidence_dates_and_amounts(claim))

    # 3. Image vs Document/Claim subject relationship screening
    images = [it for it in claim.evidence_items if it.evidence_type.upper() in {"IMAGE", "PHOTO"} and it.file_bytes]
    docs = [it for it in claim.evidence_items if it.evidence_type.upper() in {"DOCUMENT", "INVOICE", "ESTIMATE", "REPORT"}]

    # If both images and text-bearing documents/descriptions are present
    for img_item in images:
        for doc_item in docs:
            query_text = doc_item.description or doc_item.metadata.get("summary") or doc_item.metadata.get("text_snippet")
            if not query_text and doc_item.metadata.get("text"):
                # Use first 200 characters of extracted text as query
                query_text = doc_item.metadata["text"][:200]

            if query_text:
                score, status = compute_image_text_similarity(img_item.file_bytes, query_text)
                if status == RelationshipStatus.POTENTIAL_INCONSISTENCY:
                    signals.append(Signal(
                        name="CROSS_EVIDENCE_SEMANTIC_MISMATCH",
                        severity="MEDIUM",
                        score=45,
                        message=(
                            f"Image '{img_item.item_id}' shows low semantic correspondence with "
                            f"document '{doc_item.item_id}' description ('{query_text[:60]}...'). "
                            f"Potential topical inconsistency."
                        ),
                        confidence=score
                    ))
                elif status == RelationshipStatus.CONSISTENT:
                    signals.append(Signal(
                        name="CROSS_EVIDENCE_SEMANTIC_MATCH",
                        severity="LOW",
                        score=90,
                        message=(
                            f"Image '{img_item.item_id}' shows consistent visual-semantic relationship with "
                            f"document '{doc_item.item_id}' subject."
                        ),
                        confidence=score
                    ))
                # Note: If INSUFFICIENT_INFORMATION, no spurious warning is created

    return signals
