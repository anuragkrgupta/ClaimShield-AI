"""
Adapter and orchestration layer connecting document extraction to claim evidence
and claim consistency checks for ClaimShield AI.
"""
import logging
import re
from datetime import date
from typing import List, Optional, Tuple, Union, Any

from core.types import Signal
from core.claim.models import Claim, EvidenceItem
from core.claim.consistency import (
    verify_claim_consistency,
    _parse_date,
    _parse_amount,
)
from core.claim.cross_evidence import verify_cross_evidence
from core.document.extractor import ExtractedDocument, extract_document
from core.document.tampering import (
    check_document_tampering,
    check_document_authenticity,
)

logger = logging.getLogger(__name__)


def resolve_document_date(doc: ExtractedDocument) -> Tuple[Optional[str], List[str], bool]:
    """
    Safely resolves a single deterministic date from an ExtractedDocument.
    Returns (resolved_date, candidate_dates, is_ambiguous).

    Rules:
    - If 0 candidate dates: (None, [], False).
    - If 1 candidate date: (doc.dates[0], doc.dates, False).
    - If >1 candidate dates:
        - Normalize via _parse_date.
        - If all valid parsed dates point to the exact same calendar date: (doc.dates[0], doc.dates, False).
        - If multiple distinct calendar dates or ambiguous formats exist: (None, doc.dates, True).
          Does not arbitrarily choose one candidate over another.
    """
    if not doc.dates:
        return None, [], False

    if len(doc.dates) == 1:
        return doc.dates[0], list(doc.dates), False

    parsed_dates = set()
    has_unresolved = False

    for d_str in doc.dates:
        p_date, valid, ambig = _parse_date(d_str)
        if valid and not ambig and p_date is not None:
            parsed_dates.add(p_date)
        else:
            has_unresolved = True

    # If all candidate strings resolve to the exact same calendar date
    if len(parsed_dates) == 1 and not has_unresolved:
        return doc.dates[0], list(doc.dates), False

    # Multiple distinct dates or unresolved ambiguity: do not arbitrarily choose
    return None, list(doc.dates), True


def _clean_amount_str(val: str) -> str:
    """Strips leading text labels like 'Total: ', 'Balance Due: ' for monetary parsing."""
    cleaned = re.sub(
        r"^(?:total|amount|subtotal|balance|due|paid|fee)[\s:]*",
        "",
        val.strip(),
        flags=re.IGNORECASE,
    ).strip()
    return cleaned


def resolve_document_amount(doc: ExtractedDocument) -> Tuple[Optional[str], List[str], bool]:
    """
    Safely resolves a single deterministic monetary amount from an ExtractedDocument.
    Returns (resolved_amount, candidate_amounts, is_ambiguous).

    Rules:
    - If 0 candidate amounts: (None, [], False).
    - If 1 candidate amount: (_clean_amount_str(doc.amounts[0]), doc.amounts, False).
    - If >1 candidate amounts:
        - Normalize via _parse_amount.
        - If all valid parsed amounts resolve to the exact same numeric Decimal:
          (clean_str, doc.amounts, False).
        - If multiple distinct numeric amounts exist: (None, doc.amounts, True).
          Does not arbitrarily choose one candidate over another.
    """
    if not doc.amounts:
        return None, [], False

    if len(doc.amounts) == 1:
        return _clean_amount_str(doc.amounts[0]), list(doc.amounts), False

    parsed_amounts = {}
    has_unresolved = False

    for a_str in doc.amounts:
        clean_str = _clean_amount_str(a_str)
        p_amt, valid = _parse_amount(clean_str)
        if valid and p_amt is not None:
            if p_amt not in parsed_amounts or any(sym in clean_str for sym in ("$", "€", "£", "₹")):
                parsed_amounts[p_amt] = clean_str
        else:
            has_unresolved = True

    # If all candidate strings resolve to the exact same finite amount
    if len(parsed_amounts) == 1 and not has_unresolved:
        return list(parsed_amounts.values())[0], list(doc.amounts), False

    # Multiple distinct amounts: do not arbitrarily choose
    return None, list(doc.amounts), True


def document_to_evidence_item(
    doc: ExtractedDocument,
    item_id: str = "DOC-1",
    evidence_type: str = "DOCUMENT",
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    description: Optional[str] = None,
    extracted_date: Optional[Union[date, str]] = None,
    extracted_amount: Optional[Union[float, int, str]] = None,
    attach_document_signals: bool = True,
    metadata_overrides: Optional[dict] = None,
) -> EvidenceItem:
    """
    Adapts an ExtractedDocument into an EvidenceItem data model.
    Preserves text, extracted identifiers, candidate dates/amounts, and tampering signals.
    """
    # 1. Resolve date safely
    if extracted_date is not None:
        chosen_date = extracted_date
        cand_dates = list(doc.dates)
        is_date_ambig = False
    else:
        chosen_date, cand_dates, is_date_ambig = resolve_document_date(doc)

    # 2. Resolve amount safely
    if extracted_amount is not None:
        chosen_amount = extracted_amount
        cand_amts = list(doc.amounts)
        is_amt_ambig = False
    else:
        chosen_amount, cand_amts, is_amt_ambig = resolve_document_amount(doc)

    # 3. Assemble metadata
    meta = {
        "identifiers": list(doc.identifiers),
        "candidate_dates": cand_dates,
        "candidate_amounts": cand_amts,
        "has_ambiguous_dates": is_date_ambig,
        "has_ambiguous_amounts": is_amt_ambig,
        "text": doc.text,
        "text_snippet": doc.text[:200] if doc.text else "",
        "document_format": doc.metadata.format,
        "page_count": doc.metadata.page_count,
        "producer": doc.metadata.producer,
        "creator": doc.metadata.creator,
        "creation_date": doc.metadata.creation_date,
        "mod_date": doc.metadata.mod_date,
        "document_metadata_raw": doc.metadata.metadata_raw,
        "extracted_document": doc,
    }

    # Extract claim ID if explicitly referenced in document text or metadata
    claim_id = None
    if doc.metadata.metadata_raw and "claim_id" in doc.metadata.metadata_raw:
        raw_val = doc.metadata.metadata_raw["claim_id"]
        if raw_val is not None and not isinstance(raw_val, bool):
            candidate = str(raw_val).strip()
            cand_lower = candidate.lower()
            cand_upper = candidate.upper()
            has_digit = any(c.isdigit() for c in candidate)
            has_marker = cand_upper.startswith(("CLM-", "CLAIM-", "CLM_", "CLAIM_"))
            if (
                candidate
                and cand_lower not in {"none", "null", "false", "pending", "unknown"}
                and not cand_upper.startswith(("POL-", "POLICY", "INV-", "INVOICE", "REC-", "RECEIPT", "EST-", "ESTIMATE"))
                and (has_digit or has_marker)
            ):
                claim_id = candidate

    if not claim_id and doc.text:
        # Require an explicit claim-identifier label or claim marker, and require either an explicit
        # claim marker (e.g. CLM-, CLAIM-) or a captured value containing at least one digit.
        # Headings like 'Claim Type:', 'Claim Details:', 'Claim Status:' or policy/invoice numbers must not match.
        pattern = (
            r"\bclaim\s*(?:#|(?:id|number|num|reference|ref|no)\b\.?)\s*[:\-#]?\s*"
            r"((?=[A-Za-z0-9\-_/]{3,30}\b)(?:(?:CLM|CLAIM)[\-_][A-Za-z0-9\-_/]+|[A-Za-z0-9\-_/]*\d[A-Za-z0-9\-_/]*))\b"
            r"|\bclaim\s*[:\-]?\s*((?:CLM|CLAIM)[\-_][A-Za-z0-9\-_/]{2,30})\b"
        )
        for match in re.finditer(pattern, doc.text, re.IGNORECASE):
            val = (match.group(1) or match.group(2) or "").strip()
            if not val:
                continue
            val_lower = val.lower()
            val_upper = val.upper()
            if (
                val_lower in {"number", "date", "amount", "total", "invoice", "receipt", "claim", "policy", "reference", "none", "null", "pending", "unknown"}
                or val_upper.startswith(("POL-", "POLICY", "INV-", "INVOICE", "REC-", "RECEIPT", "EST-", "ESTIMATE"))
            ):
                continue

            has_digit = any(c.isdigit() for c in val)
            has_claim_marker = val_upper.startswith(("CLM-", "CLAIM-", "CLM_", "CLAIM_"))
            if not (has_digit or has_claim_marker):
                continue

            claim_id = val
            break

    if claim_id:
        meta["claim_id"] = claim_id

    # 4. Attach document tampering and authenticity signals if requested
    if attach_document_signals:
        doc_signals: List[Signal] = []
        doc_signals.extend(check_document_tampering(doc))
        doc_signals.extend(check_document_authenticity(doc))
        meta["document_signals"] = doc_signals

    if metadata_overrides:
        meta.update(metadata_overrides)

    return EvidenceItem(
        item_id=item_id,
        evidence_type=evidence_type,
        file_path=file_path,
        file_bytes=file_bytes,
        extracted_date=chosen_date,
        extracted_amount=chosen_amount,
        description=description or meta.get("text_snippet"),
        metadata=meta,
    )


def document_file_to_evidence_item(
    file_bytes: bytes,
    filename: Optional[str] = None,
    item_id: str = "DOC-1",
    evidence_type: str = "DOCUMENT",
    description: Optional[str] = None,
) -> Tuple[Optional[EvidenceItem], bool]:
    """
    Extracts an ExtractedDocument from raw file bytes and maps it into an EvidenceItem.
    Returns (evidence_item, success).
    """
    if not file_bytes:
        return None, False

    doc, ok = extract_document(file_bytes, filename=filename)
    if not ok or doc is None:
        return None, False

    item = document_to_evidence_item(
        doc=doc,
        item_id=item_id,
        evidence_type=evidence_type,
        file_path=filename,
        file_bytes=file_bytes,
        description=description,
    )
    return item, True


def analyze_claim(claim: Claim) -> List[Signal]:
    """
    Lightweight orchestration connecting document analysis, claim consistency,
    and cross-evidence verification.

    Executes:
    1. Document tampering and authenticity signals from claim evidence items.
    2. Date/amount ambiguity notifications when multiple candidates prevented safe assumption.
    3. Deterministic claim consistency checks (dates and amounts).
    4. Cross-evidence verification (identifiers, date/amount sufficiency, semantic similarity).

    Returns a consolidated list of explainable Signal objects.
    """
    signals: List[Signal] = []

    # 1. Document-level tampering, authenticity, and candidate ambiguity signals
    for item in claim.evidence_items:
        meta = item.metadata or {}
        # Document tampering & authenticity signals
        if "document_signals" in meta:
            doc_signals = meta["document_signals"]
            if isinstance(doc_signals, (list, tuple)):
                for s in doc_signals:
                    if isinstance(s, Signal):
                        signals.append(s)
            elif isinstance(doc_signals, Signal):
                signals.append(doc_signals)
            # If doc_signals is None or another unsupported value, do nothing safely
        elif "extracted_document" in meta and isinstance(meta["extracted_document"], ExtractedDocument):
            doc = meta["extracted_document"]
            signals.extend(check_document_tampering(doc))
            signals.extend(check_document_authenticity(doc))

        # Informational notification when multiple candidate dates / amounts were detected
        if meta.get("has_ambiguous_dates"):
            cand_dates = meta.get("candidate_dates", [])
            dates_str = ", ".join(cand_dates)
            signals.append(Signal(
                name="DOCUMENT_MULTIPLE_DATES_DETECTED",
                severity="LOW",
                score=70,
                message=(
                    f"Evidence item '{item.item_id}' contains multiple candidate dates ({dates_str}). "
                    f"A primary evidence date was not assumed."
                ),
            ))

        if meta.get("has_ambiguous_amounts"):
            cand_amts = meta.get("candidate_amounts", [])
            amts_str = ", ".join(cand_amts)
            signals.append(Signal(
                name="DOCUMENT_MULTIPLE_AMOUNTS_DETECTED",
                severity="LOW",
                score=70,
                message=(
                    f"Evidence item '{item.item_id}' contains multiple candidate monetary amounts ({amts_str}). "
                    f"A primary evidence amount was not assumed."
                ),
            ))

    # 2. Deterministic claim consistency checks (incident vs filing date, evidence dates vs incident, amounts)
    signals.extend(verify_claim_consistency(claim))

    # 3. Cross-evidence verification (claim ID matches, data sufficiency, image-text correspondence)
    signals.extend(verify_cross_evidence(claim))

    return signals
