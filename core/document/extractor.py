"""
Document text, metadata, and field extraction for ClaimShield AI.
Supports PDF documents (via PyMuPDF) and image documents (via PyTesseract / PIL).
"""
import io
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import pymupdf as fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Extracted metadata attributes from document header/format."""
    format: str  # "PDF", "IMAGE", "UNKNOWN"
    page_count: int = 1
    producer: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None
    metadata_raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    """Encapsulates raw text, structured fields, and metadata extracted from a document."""
    text: str
    metadata: DocumentMetadata
    dates: List[str] = field(default_factory=list)
    amounts: List[str] = field(default_factory=list)
    identifiers: List[str] = field(default_factory=list)  # Invoice numbers, policy IDs, reference IDs
    keywords: List[str] = field(default_factory=list)


def _extract_dates_from_text(text: str) -> List[str]:
    """Extracts date strings using common standard formats."""
    # Matches patterns like 2026-05-12, 12-05-2026, 05/12/2026, 2026/05/12, May 12, 2026, 12 May 2026
    date_patterns = [
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b",
    ]
    found = []
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found.append(match.group(0).strip())
    # Return unique dates preserving order
    seen = set()
    result = []
    for d in found:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result


def _extract_amounts_from_text(text: str) -> List[str]:
    """Extracts monetary amounts from text."""
    # Matches currency symbols and labels with numbers: $1,250.00, $1250.00, EUR 500, Rs. 1000, Total: 450.00, Total: 1250.00
    # Enforces that the complete numeric token is valid; malformed numbers (e.g. $1250.001 with extra decimal digits
    # or $1,25.00 with invalid grouping) are completely rejected rather than partially matched.
    valid_num_pattern = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?$")

    candidate_patterns = [
        r"([\$€£₹]\s*)([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)(?![0-9A-Za-z]|[\.,][0-9])",
        r"(\b(?:USD|EUR|GBP|INR|CAD|AUD)\s*)([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)(?![0-9A-Za-z]|[\.,][0-9])",
        r"((?<![A-Za-z0-9_-])(?:total|amount|subtotal|balance|due|paid|fee)[\s:]*[\$€£₹]?\s*)([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)(?![0-9A-Za-z]|[\.,][0-9])",
    ]

    found = []
    for pattern in candidate_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            full_match = match.group(0).strip()
            num_str = match.group(2).strip()
            # If the complete numeric token matches standard grouped or ungrouped amount format
            if valid_num_pattern.match(num_str):
                found.append(full_match)


    # Deduplicate
    seen = set()
    result = []
    for a in found:
        if a not in seen:
            seen.add(a)
            result.append(a)
    return result




def _extract_identifiers_from_text(text: str) -> List[str]:
    """Extracts document reference IDs such as Invoice #, Policy #, Claim #, Ref #."""
    id_patterns = [
        r"(?:invoice|receipt|policy|claim|estimate|order|reference|ref|bill|id)\s*(?:#|no\.?|num|number)?\s*[:\-]?\s*([A-Za-z0-9\-_/]{4,25})\b",
    ]
    found = []
    for pattern in id_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            val = match.group(1).strip()
            if not val.lower() in {"number", "date", "amount", "total", "invoice", "receipt", "claim"}:
                found.append(val)
    seen = set()
    result = []
    for item in found:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_document(file_bytes: bytes, filename: Optional[str] = None) -> Tuple[Optional[ExtractedDocument], bool]:
    """
    Extracts text, metadata, dates, amounts, and identifiers from PDF or image bytes.
    Returns (extracted_document, success).
    If file is empty or completely unreadable, returns (None, False).
    """
    if not file_bytes:
        return None, False

    is_pdf = file_bytes.startswith(b"%PDF") or (filename and filename.lower().endswith(".pdf"))

    if is_pdf:
        return _extract_from_pdf(file_bytes)
    else:
        return _extract_from_image(file_bytes)


def _extract_from_pdf(pdf_bytes: bytes) -> Tuple[Optional[ExtractedDocument], bool]:
    """Extracts text and metadata from a PDF file using PyMuPDF and per-page OCR fallback."""
    if not PYMUPDF_AVAILABLE:
        logger.error("PyMuPDF / fitz is not installed; cannot process PDF.")
        return None, False

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF stream: {e}")
        return None, False

    try:
        page_count = len(doc)
        full_text_list = []
        for page_idx in range(page_count):
            page = doc[page_idx]
            page_text = page.get_text()
            if page_text and page_text.strip():
                full_text_list.append(page_text.strip())
            elif PYTESSERACT_AVAILABLE and page_idx < 5:  # OCR fallback per page if digital text layer is empty
                try:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_page = pytesseract.image_to_string(img)
                    if ocr_page and ocr_page.strip():
                        full_text_list.append(ocr_page.strip())
                except Exception as e:
                    logger.warning(f"OCR failed on PDF page {page_idx}: {e}")

        full_text = "\n".join(full_text_list).strip()

        meta_dict = doc.metadata or {}
        metadata = DocumentMetadata(
            format="PDF",
            page_count=page_count,
            producer=meta_dict.get("producer"),
            creator=meta_dict.get("creator"),
            creation_date=meta_dict.get("creationDate"),
            mod_date=meta_dict.get("modDate"),
            metadata_raw=meta_dict,
        )

        dates = _extract_dates_from_text(full_text)
        amounts = _extract_amounts_from_text(full_text)
        identifiers = _extract_identifiers_from_text(full_text)

        return ExtractedDocument(
            text=full_text,
            metadata=metadata,
            dates=dates,
            amounts=amounts,
            identifiers=identifiers,
        ), True

    except Exception as e:
        logger.error(f"Error extracting PDF contents: {e}")
        return None, False
    finally:
        doc.close()


def _extract_from_image(image_bytes: bytes) -> Tuple[Optional[ExtractedDocument], bool]:
    """Extracts text and metadata from an image file using PIL and PyTesseract."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Failed to open image bytes: {e}")
        return None, False

    try:
        text = ""
        if PYTESSERACT_AVAILABLE:
            try:
                text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                logger.warning(f"PyTesseract OCR failed: {e}")

        # Basic image metadata
        exif_data = {}
        if hasattr(img, "_getexif") and img._getexif():
            exif_data = {str(k): str(v) for k, v in img._getexif().items()}

        software_tag = exif_data.get("305") or exif_data.get("Software")

        metadata = DocumentMetadata(
            format=img.format or "IMAGE",
            page_count=1,
            producer=software_tag,
            creator=software_tag,
            creation_date=exif_data.get("36867") or exif_data.get("DateTimeOriginal"),
            mod_date=exif_data.get("306") or exif_data.get("DateTime"),
            metadata_raw=exif_data,
        )

        dates = _extract_dates_from_text(text)
        amounts = _extract_amounts_from_text(text)
        identifiers = _extract_identifiers_from_text(text)

        return ExtractedDocument(
            text=text,
            metadata=metadata,
            dates=dates,
            amounts=amounts,
            identifiers=identifiers,
        ), True

    except Exception as e:
        logger.error(f"Error extracting image document: {e}")
        return None, False
