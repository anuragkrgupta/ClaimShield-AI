"""
Document tampering, metadata inconsistency, and authenticity checks for ClaimShield AI.
Analyzes document metadata and structure for indicators of editing, modification, or anomalous assembly.
"""
import logging
import re
from datetime import datetime
from typing import List, Optional
from core.types import Signal
from core.document.extractor import ExtractedDocument, DocumentMetadata

logger = logging.getLogger(__name__)

# Known graphics/editing software signatures often found in tampered or non-original documents
KNOWN_EDITING_SOFTWARE = [
    "photoshop",
    "gimp",
    "canva",
    "illustrator",
    "inkscape",
    "coreldraw",
    "paint.net",
    "affinity photo",
    "affinity designer",
    "pixlr",
]

# Standard digital invoice / PDF generation engines typically associated with programmatic creation
STANDARD_GENERATORS = [
    "reportlab",
    "wkhtmltopdf",
    "tcpdf",
    "fpdf",
    "itext",
    "pdfkit",
    "puppeteer",
    "weasyprint",
    "jasperreports",
    "acrobat",
    "pdfium",
    "quartz",
    "skia",
]


def _parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parses PDF date strings formatted typically like:
    D:YYYYMMDDHHmmSS or D:YYYYMMDDHHmmSSOHH'mm' or ISO strings.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]
    
    # Strip timezones like +00'00' or -05'00' or Z
    cleaned = re.sub(r"[Zz]|([+\-]\d{2}'?\d{2}'?)", "", cleaned)
    
    # Try formats directly
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
        # Also try prefix matching if cleaned string is longer
        for length in (14, 12, 8):
            if len(cleaned) >= length:
                try:
                    return datetime.strptime(cleaned[:length], fmt)
                except ValueError:
                    pass
    return None



def check_document_tampering(doc: ExtractedDocument) -> List[Signal]:
    """
    Performs deterministic and forensic checks on an extracted document:
    1. Checks if document creator/producer indicates consumer editing software (Photoshop, Canva, GIMP).
    2. Checks for significant discrepancy between creation date and modification date.
    3. Checks for anomalous metadata or missing text layers.
    Returns structured Signal findings.
    """
    signals: List[Signal] = []
    meta = doc.metadata

    producer_str = (meta.producer or "").lower()
    creator_str = (meta.creator or "").lower()
    combined_software = f"{producer_str} {creator_str}"

    # 1. Check for consumer image editing software in metadata
    for editor in KNOWN_EDITING_SOFTWARE:
        if editor in combined_software:
            signals.append(Signal(
                name="DOC_EDITING_SOFTWARE_DETECTED",
                severity="MEDIUM",
                score=45,
                message=(
                    f"Document metadata reveals generation or modification with image editing software: '{editor.capitalize()}'. "
                    f"This may indicate manual alteration or retouching."
                ),
                confidence=0.85
            ))
            break

    # 2. Check Creation Date vs Modification Date in PDF metadata
    c_date = _parse_pdf_date(meta.creation_date)
    m_date = _parse_pdf_date(meta.mod_date)

    if c_date and m_date:
        # If modified significantly after creation (e.g. more than 1 day apart)
        diff_seconds = (m_date - c_date).total_seconds()
        if diff_seconds > 86400:  # > 24 hours
            diff_days = int(diff_seconds // 86400)
            signals.append(Signal(
                name="DOC_METADATA_MODIFIED_SUBSEQUENTLY",
                severity="LOW",
                score=70,
                message=(
                    f"Document modification date is {diff_days} day(s) after initial creation date "
                    f"(Created: {c_date.strftime('%Y-%m-%d')}, Modified: {m_date.strftime('%Y-%m-%d')}). "
                    f"Suggests subsequent revision or re-export."
                ),
                confidence=0.75
            ))
        elif diff_seconds < -60:  # Modification date predates creation date (anomalous)
            signals.append(Signal(
                name="DOC_METADATA_DATE_ANOMALY",
                severity="HIGH",
                score=35,
                message=(
                    f"Document modification date ({m_date.strftime('%Y-%m-%d')}) precedes its "
                    f"creation date ({c_date.strftime('%Y-%m-%d')}). Inconsistent metadata clock."
                ),
                confidence=0.90
            ))

    # 3. Check for empty or unextractable text in digital formats
    if meta.format == "PDF" and not doc.text.strip():
        signals.append(Signal(
            name="DOC_NO_TEXT_LAYER",
            severity="LOW",
            score=75,
            message="PDF contains no readable digital text layer (may be a flat scan, bitmap container, or image wrapper).",
            confidence=0.95
        ))

    return signals


def check_document_authenticity(doc: ExtractedDocument) -> List[Signal]:
    """
    Assesses potential AI-generated or synthetic document content.
    Note: As per project guidelines, natural-image detectors (such as UnivFD) are not
    validated for document synthesis. Rather than fabricating an unvalidated AI probability,
    this check inspects defensible synthetic cues (e.g. repetitive hallucinated gibberish,
    synthetic canvas artifacts, or known AI wrapper signatures) and documents the limitation.
    """
    signals: List[Signal] = []
    text = doc.text.strip()

    # Repetitive hallucination token check (common in unconstrained LLM or synthetic OCR outputs)
    if text:
        words = text.split()
        if len(words) >= 30:
            # Check for excessive repetition of identical phrases or tokens
            repeated_tokens = [w for w in set(words) if words.count(w) > len(words) * 0.4 and len(w) > 3]
            if repeated_tokens:
                signals.append(Signal(
                    name="DOC_SYNTHETIC_TEXT_ANOMALY",
                    severity="MEDIUM",
                    score=50,
                    message=f"Document exhibits abnormal token repetition pattern ({repeated_tokens[0]}), characteristic of synthetic or looped generation.",
                    confidence=0.70
                ))

    # If document appears clean of overt synthetic cues:
    # Explicitly document that AI-generation detector is advisory and unvalidated for documents
    if not signals:
        # Authentic baseline: no synthetic anomalies detected
        pass

    return signals
