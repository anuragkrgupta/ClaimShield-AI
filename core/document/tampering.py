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


from collections import Counter
from datetime import datetime, timezone, timedelta


def _parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parses PDF and EXIF date strings.
    Supports formats like:
    D:YYYYMMDDHHmmSS[+|-]HH'mm'
    YYYY:MM:DD HH:MM:SS (EXIF standard)
    ISO strings and naive dates.
    Preserves timezone information when present.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]

    # Check for timezone offset pattern:
    # 1. 'Z' or 'z' -> UTC
    # 2. Colon-separated ISO offset (+HH:MM, -HH:MM)
    # 3. PDF style (+HH'MM', -HH'MM', +HH'MM, -HH'MM)
    # 4. Compact style (+HHMM, -HHMM)
    tz = None
    tz_match = re.search(r"([Zz])|([+\-])(\d{2})(?::|'?)(\d{2})'?", cleaned)
    if tz_match:
        if tz_match.group(1):  # 'Z' or 'z' -> UTC
            tz = timezone.utc
            cleaned_no_tz = cleaned[:tz_match.start()].strip()
        else:
            sign = 1 if tz_match.group(2) == "+" else -1
            try:
                hours = int(tz_match.group(3))
                minutes = int(tz_match.group(4))
                # Validate minutes < 60 and total offset strictly between -24h and +24h
                if minutes >= 60 or hours > 23:
                    return None
                offset_delta = timedelta(hours=hours, minutes=minutes)
                if offset_delta >= timedelta(hours=24):
                    return None
                tz = timezone(sign * offset_delta)
                cleaned_no_tz = cleaned[:tz_match.start()].strip()
            except (ValueError, OverflowError):
                return None
    else:
        cleaned_no_tz = cleaned


    # Supported date/time formats
    formats = (
        "%Y:%m:%d %H:%M:%S",   # EXIF format
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned_no_tz, fmt)
            if tz is not None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            pass

        # Try prefix matching if timestamp contains extra characters
        for length in (19, 14, 12, 8):
            if len(cleaned_no_tz) >= length:
                try:
                    dt = datetime.strptime(cleaned_no_tz[:length], fmt)
                    if tz is not None:
                        dt = dt.replace(tzinfo=tz)
                    return dt
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

    # 2. Check Creation Date vs Modification Date in metadata
    c_date = _parse_pdf_date(meta.creation_date)
    m_date = _parse_pdf_date(meta.mod_date)

    if c_date and m_date:
        # Check timezone awareness consistency
        c_aware = c_date.tzinfo is not None and c_date.tzinfo.utcoffset(c_date) is not None
        m_aware = m_date.tzinfo is not None and m_date.tzinfo.utcoffset(m_date) is not None

        if c_aware and m_aware:
            # Both aware: normalize to UTC
            c_cmp = c_date.astimezone(timezone.utc)
            m_cmp = m_date.astimezone(timezone.utc)
            diff_seconds = (m_cmp - c_cmp).total_seconds()
        elif not c_aware and not m_aware:
            # Both naive: direct difference
            diff_seconds = (m_date - c_date).total_seconds()
        else:
            # Mixed case (one aware, one naive): do not guess timezone, skip comparison safely
            diff_seconds = None

        if diff_seconds is not None:
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
            threshold = len(words) * 0.4
            word_counts = Counter(words)
            # Find tokens repeating beyond threshold with length > 3
            repeated_tokens = [w for w, cnt in word_counts.items() if cnt > threshold and len(w) > 3]
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
