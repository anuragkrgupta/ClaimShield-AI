"""
Unit and integration tests for Phase 5 Document Analysis and Cross-Evidence Verification.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from core.document.extractor import (
    DocumentMetadata,
    ExtractedDocument,
    extract_document,
    _extract_dates_from_text,
    _extract_amounts_from_text,
    _extract_identifiers_from_text,
)
from core.document.tampering import (
    check_document_tampering,
    check_document_authenticity,
)
from core.claim.models import Claim, EvidenceItem
from core.claim.cross_evidence import (
    check_identifier_consistency,
    check_cross_evidence_dates_and_amounts,
    compute_image_text_similarity,
    verify_cross_evidence,
    RelationshipStatus,
)


def _create_minimal_pdf_bytes(text: str = "Test Invoice #INV-1234\nDate: 2026-05-15\nTotal: $1,250.00") -> bytes:
    """Creates in-memory PDF bytes with text layer using PyMuPDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def _create_test_image_bytes(color: str = "white") -> bytes:
    img = Image.new("RGB", (120, 120), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------
# 1. Extraction Tests
# ---------------------------------------------------------

def test_extract_dates_amounts_identifiers_regex():
    sample_text = (
        "Invoice Number: INV-98765\n"
        "Billed on 2026-04-12.\n"
        "Payment due by May 15, 2026.\n"
        "Total Amount Due: $3,450.75\n"
        "Policy Ref: POL-A109\n"
    )
    dates = _extract_dates_from_text(sample_text)
    assert "2026-04-12" in dates
    assert "May 15, 2026" in dates

    amounts = _extract_amounts_from_text(sample_text)
    assert any("3,450.75" in a for a in amounts)

    identifiers = _extract_identifiers_from_text(sample_text)
    assert "INV-98765" in identifiers or "POL-A109" in identifiers


def test_extract_amounts_boundaries_and_malformed_rejection():
    """Verify valid amounts are captured and malformed amounts/partial numbers are rejected."""
    # Valid amounts: grouped, ungrouped, decimal, and labelled
    valid_text = (
        "Item 1: $1250.00\n"
        "Item 2: $1,250.00\n"
        "Total: 1250.00\n"
        "Subtotal: $450\n"
        "Balance: EUR 5000.50\n"
        "Sentence ending with period: Paid $1250.\n"
        "Sentence ending with comma: Paid $1,250, then left.\n"
    )
    valid_amounts = _extract_amounts_from_text(valid_text)
    assert "$1250.00" in valid_amounts
    assert "$1,250.00" in valid_amounts
    assert "Total: 1250.00" in valid_amounts
    assert "Subtotal: $450" in valid_amounts
    assert "EUR 5000.50" in valid_amounts
    assert "$1250" in valid_amounts or "$1,250" in valid_amounts

    # Malformed amounts must NOT be partially matched as $1250 or $1250.00
    # $1250.001 has 3 decimal places; must not extract $1250 or $1250.00
    malformed_dec = _extract_amounts_from_text("Invalid amount: $1250.001")
    assert malformed_dec == []

    # Malformed grouping: $1,25.00 (2 digits in group); must not match
    malformed_grp = _extract_amounts_from_text("Invalid grouping: $1,25.00")
    assert malformed_grp == []

    # Malformed grouping without decimals: $1,25,00
    assert _extract_amounts_from_text("Invalid grouping: $1,25,00") == []

    # Adjacent letters/alphanumeric characters: $1250.00a or $1250a
    assert _extract_amounts_from_text("Malformed suffix: $1250.00a") == []
    assert _extract_amounts_from_text("Malformed suffix: $1250a") == []

    # Total with malformed decimal: Total: 1250.001
    assert _extract_amounts_from_text("Summary Total: 1250.001") == []

    # Adjacent dot and continuing digits: $1250.00.50
    assert _extract_amounts_from_text("Double decimal: $1250.00.50") == []



def test_pdf_extraction_valid():
    pdf_bytes = _create_minimal_pdf_bytes("Property Repair Receipt #REC-5542\nDate: 2026-06-10\nTotal: $450.00")
    extracted, success = extract_document(pdf_bytes, filename="receipt.pdf")
    assert success is True
    assert extracted is not None
    assert extracted.metadata.format == "PDF"
    assert "REC-5542" in extracted.text
    assert len(extracted.dates) >= 1
    assert any("450" in a for a in extracted.amounts)


def test_empty_and_malformed_document_extraction():
    # Empty bytes
    doc, ok = extract_document(b"")
    assert ok is False
    assert doc is None

    # Corrupt / garbage bytes
    doc, ok = extract_document(b"this is completely corrupted not a pdf or image")
    assert ok is False
    assert doc is None


def test_image_document_extraction():
    img_bytes = _create_test_image_bytes()
    doc, ok = extract_document(img_bytes, filename="scan.jpg")
    assert ok is True
    assert doc is not None
    assert doc.metadata.format in ("JPEG", "IMAGE")


# ---------------------------------------------------------
# 2. Document Tampering & Authenticity Tests
# ---------------------------------------------------------

def test_legitimate_document_not_flagged():
    doc = ExtractedDocument(
        text="Standard Official Invoice\nItem: Roof Inspection\nCost: $800.00",
        metadata=DocumentMetadata(
            format="PDF",
            producer="ReportLab PDF Library - version 3.5",
            creation_date="D:20260510120000",
            mod_date="D:20260510120000",
        ),
        dates=["2026-05-10"],
        amounts=["$800.00"],
    )
    signals = check_document_tampering(doc)
    assert len(signals) == 0

    auth_signals = check_document_authenticity(doc)
    assert len(auth_signals) == 0


def test_document_tampering_editing_software_detected():
    doc = ExtractedDocument(
        text="Modified Estimate Document",
        metadata=DocumentMetadata(
            format="PDF",
            producer="Adobe Photoshop 24.1",
            creator="Photoshop Export Engine",
        ),
    )
    signals = check_document_tampering(doc)
    assert len(signals) == 1
    assert signals[0].name == "DOC_EDITING_SOFTWARE_DETECTED"
    assert signals[0].severity == "MEDIUM"
    assert "Photoshop" in signals[0].message


def test_document_tampering_metadata_date_discrepancy():
    doc = ExtractedDocument(
        text="Re-saved Contract",
        metadata=DocumentMetadata(
            format="PDF",
            creation_date="D:20260101100000",
            mod_date="D:20260520150000",  # Modified 140 days later
        ),
    )
    signals = check_document_tampering(doc)
    assert len(signals) == 1
    assert signals[0].name == "DOC_METADATA_MODIFIED_SUBSEQUENTLY"
    assert signals[0].severity == "LOW"


def test_extract_amounts_grouped_and_ungrouped_boundaries():
    text = (
        "Item 1: $1250.00, Item 2: $1,250.00, Item 3: EUR 5000.50, "
        "Total: 1250.00, Balance: 45000, Non-amount: 123456789abc"
    )
    amounts = _extract_amounts_from_text(text)
    assert any("$1250.00" in a for a in amounts)
    assert any("$1,250.00" in a for a in amounts)
    assert any("EUR 5000.50" in a for a in amounts)
    assert any("Total: 1250.00" in a or "1250.00" in a for a in amounts)
    assert any("Balance: 45000" in a or "45000" in a for a in amounts)
    # Ensure boundary prevents matching partial prefix of longer numbers without boundary
    assert not any(a == "$12" for a in amounts)


def test_extract_amounts_rejects_malformed_tails_and_grouping():
    # $1250.001 has 3 decimal digits -> must NOT extract partial '$1250.00' or '$1250'
    text_malformed_decimals = "Invalid: $1250.001 and Total: 400.123"
    amts1 = _extract_amounts_from_text(text_malformed_decimals)
    assert not any("$1250" in a for a in amts1)
    assert not any("400" in a for a in amts1)

    # Malformed grouping like $1,25.00 has 2 digits between commas -> must NOT match
    text_malformed_grouping = "Invalid: $1,25.00 and $12,3.45"
    amts2 = _extract_amounts_from_text(text_malformed_grouping)
    assert not any("$1,25" in a for a in amts2)
    assert not any("$12,3" in a for a in amts2)



def test_exif_software_tampering_detection():
    # EXIF software tag 305 set to Canva or Photoshop
    doc = ExtractedDocument(
        text="Scanned Receipt",
        metadata=DocumentMetadata(
            format="JPEG",
            producer="Canva Mobile App",
            creator="Canva Mobile App",
            metadata_raw={"305": "Canva Mobile App"},
        )
    )
    signals = check_document_tampering(doc)
    assert len(signals) == 1
    assert signals[0].name == "DOC_EDITING_SOFTWARE_DETECTED"
    assert "Canva" in signals[0].message


def test_mixed_pdf_page_ocr_and_text_layer():
    # Create a 2-page PDF: page 0 has text layer, page 1 has no text (blank)
    import fitz
    doc = fitz.open()
    p0 = doc.new_page()
    p0.insert_text((50, 72), "Digital Page 1 Text")
    p1 = doc.new_page()  # Blank scanned-like page
    pdf_bytes = doc.write()
    doc.close()

    with patch("core.document.extractor.pytesseract.image_to_string", return_value="Scanned Page 2 OCR"):
        extracted, ok = extract_document(pdf_bytes, filename="mixed.pdf")
        assert ok is True
        assert extracted is not None
        assert "Digital Page 1 Text" in extracted.text
        assert "Scanned Page 2 OCR" in extracted.text


def test_pdf_ocr_failure_preserves_other_pages():
    import fitz
    doc = fitz.open()
    p0 = doc.new_page()
    p0.insert_text((50, 72), "Digital Page 1 Text")
    p1 = doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    def ocr_mock_fail(*args, **kwargs):
        raise RuntimeError("Tesseract crash on page 2")

    with patch("core.document.extractor.pytesseract.image_to_string", side_effect=ocr_mock_fail):
        extracted, ok = extract_document(pdf_bytes, filename="fail_page2.pdf")
        assert ok is True
        assert extracted is not None
        # Successfully extracted page 1 text is preserved
        assert "Digital Page 1 Text" in extracted.text


def test_exif_timestamp_format():
    from core.document.tampering import _parse_pdf_date
    exif_dt_str = "2026:05:12 12:00:00"
    dt = _parse_pdf_date(exif_dt_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 12
    assert dt.hour == 12


def test_timezone_aware_timestamp_comparisons():
    # 1. Two timestamps with same timezone
    doc_same_tz = ExtractedDocument(
        text="Doc",
        metadata=DocumentMetadata(
            format="PDF",
            creation_date="D:20260101100000+00'00'",
            mod_date="D:20260105100000+00'00'",  # 4 days later
        )
    )
    signals = check_document_tampering(doc_same_tz)
    assert any(s.name == "DOC_METADATA_MODIFIED_SUBSEQUENTLY" for s in signals)

    # 2. Two timestamps with different offsets representing the exact same instant
    # 2026-01-01 15:00:00 +05'00' == 2026-01-01 10:00:00 +00'00'
    doc_same_instant = ExtractedDocument(
        text="Doc",
        metadata=DocumentMetadata(
            format="PDF",
            creation_date="D:20260101100000+00'00'",
            mod_date="D:20260101150000+05'00'",
        )
    )
    signals = check_document_tampering(doc_same_instant)
    # Zero difference -> no discrepancy signals
    assert not any(s.name in ("DOC_METADATA_MODIFIED_SUBSEQUENTLY", "DOC_METADATA_DATE_ANOMALY") for s in signals)

    # 3. Genuine negative chronological delta
    doc_negative_delta = ExtractedDocument(
        text="Doc",
        metadata=DocumentMetadata(
            format="PDF",
            creation_date="D:20260105100000+00'00'",
            mod_date="D:20260101100000+00'00'",  # Mod is 4 days before creation
        )
    )
    signals = check_document_tampering(doc_negative_delta)
    assert any(s.name == "DOC_METADATA_DATE_ANOMALY" for s in signals)

    # 4. Mixed aware/naive timestamp pair (gracefully skipped without crash or false anomaly)
    doc_mixed = ExtractedDocument(
        text="Doc",
        metadata=DocumentMetadata(
            format="PDF",
            creation_date="D:20260101100000+00'00'",  # Aware
            mod_date="2026-01-05 10:00:00",          # Naive
        )
    )
    signals = check_document_tampering(doc_mixed)
    assert not any(s.name in ("DOC_METADATA_MODIFIED_SUBSEQUENTLY", "DOC_METADATA_DATE_ANOMALY") for s in signals)


def test_timezone_colon_iso_offsets_and_range_validation():
    from core.document.tampering import _parse_pdf_date

    # Colon-separated ISO offsets
    dt_plus = _parse_pdf_date("2026-05-12T14:30:00+02:00")
    assert dt_plus is not None
    assert dt_plus.tzinfo is not None
    assert dt_plus.utcoffset().total_seconds() == 7200

    dt_minus = _parse_pdf_date("2026-05-12T14:30:00-04:30")
    assert dt_minus is not None
    assert dt_minus.tzinfo is not None
    assert dt_minus.utcoffset().total_seconds() == -16200

    # Out-of-bounds offsets: hours >= 24 or minutes >= 60 should return None safely
    assert _parse_pdf_date("2026-05-12T14:30:00+25:00") is None
    assert _parse_pdf_date("2026-05-12T14:30:00-04:75") is None

    # No-offset timestamp remains valid naive datetime
    dt_naive = _parse_pdf_date("2026-05-12 14:30:00")
    assert dt_naive is not None
    assert dt_naive.tzinfo is None



def test_counter_repeated_tokens_preserves_behavior():
    # Exactly matches the behavior of token counting with Counter
    looped_text = "repair " * 40
    doc = ExtractedDocument(
        text=looped_text,
        metadata=DocumentMetadata(format="PDF"),
    )
    signals = check_document_authenticity(doc)
    assert len(signals) == 1
    assert signals[0].name == "DOC_SYNTHETIC_TEXT_ANOMALY"



# ---------------------------------------------------------
# 3. Cross-Evidence Relationship Tests
# ---------------------------------------------------------

def test_cross_evidence_claim_id_mismatch():
    claim = Claim(
        claim_id="CLM-7788",
        evidence_items=[
            EvidenceItem(
                item_id="DOC-1",
                evidence_type="DOCUMENT",
                metadata={"claim_id": "CLM-9999"},  # Conflicting claim ID
            )
        ]
    )
    signals = check_identifier_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "CROSS_EVIDENCE_CLAIM_ID_MISMATCH"
    assert signals[0].severity == "HIGH"
    assert "CLM-9999" in signals[0].message


def test_cross_evidence_insufficient_data():
    claim = Claim(claim_id="CLM-1000", evidence_items=[])
    signals = check_cross_evidence_dates_and_amounts(claim)
    assert len(signals) == 1
    assert signals[0].name == "CROSS_EVIDENCE_INSUFFICIENT_DATA"


@patch("core.claim.cross_evidence.compute_image_text_similarity")
def test_cross_evidence_semantic_match_and_mismatch(mock_sim):
    img_bytes = _create_test_image_bytes()
    claim = Claim(
        claim_id="CLM-5555",
        evidence_items=[
            EvidenceItem(
                item_id="IMG-1",
                evidence_type="IMAGE",
                file_bytes=img_bytes,
            ),
            EvidenceItem(
                item_id="DOC-1",
                evidence_type="DOCUMENT",
                description="Damaged kitchen countertop after pipe leak",
            ),
        ],
    )

    # Test Consistent match
    mock_sim.return_value = (0.28, RelationshipStatus.CONSISTENT)
    signals = verify_cross_evidence(claim)
    assert any(s.name == "CROSS_EVIDENCE_SEMANTIC_MATCH" for s in signals)

    # Test Inconsistent mismatch
    mock_sim.return_value = (0.05, RelationshipStatus.POTENTIAL_INCONSISTENCY)
    signals = verify_cross_evidence(claim)
    assert any(s.name == "CROSS_EVIDENCE_SEMANTIC_MISMATCH" for s in signals)

    # Test Insufficient information
    mock_sim.return_value = (0.16, RelationshipStatus.INSUFFICIENT_INFORMATION)
    signals = verify_cross_evidence(claim)
    # Insufficient info should not emit false alarm mismatch signals
    assert not any(s.name == "CROSS_EVIDENCE_SEMANTIC_MISMATCH" for s in signals)
    assert not any(s.name == "CROSS_EVIDENCE_SEMANTIC_MATCH" for s in signals)


def test_cross_evidence_non_string_identifiers():
    # Test numeric, None, float, and malformed identifiers
    claim = Claim(
        claim_id=12345,  # Numeric claim ID
        evidence_items=[
            EvidenceItem(
                item_id="DOC-1",
                evidence_type="DOCUMENT",
                metadata={"identifiers": 998877},  # Integer single identifier
            ),
            EvidenceItem(
                item_id="DOC-2",
                evidence_type="DOCUMENT",
                metadata={"identifiers": [10001, None, 20002.5]},  # Mixed non-string list
            ),
            EvidenceItem(
                item_id="DOC-3",
                evidence_type="DOCUMENT",
                metadata={"identifiers": {"invalid": "object"}},  # Non-sequence object
            ),
            EvidenceItem(
                item_id="DOC-4",
                evidence_type="DOCUMENT",
                metadata={"claim_id": 99999},  # Conflicting numeric claim ID
            ),
            EvidenceItem(
                item_id="DOC-5",
                evidence_type="DOCUMENT",
                metadata={"claim_id": 12345},  # Matching numeric claim ID
            ),
            EvidenceItem(
                item_id="DOC-6",
                evidence_type="DOCUMENT",
                metadata={"claim_id": ["list_id"]},  # Non-scalar object: should be ignored, not crash or false alarm
            ),
            EvidenceItem(
                item_id="DOC-7",
                evidence_type="DOCUMENT",
                metadata={"claim_id": {"dict_key": "val"}},  # Non-scalar object: should be ignored
            ),
        ]
    )

    signals = check_identifier_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "CROSS_EVIDENCE_CLAIM_ID_MISMATCH"
    assert "99999" in signals[0].message
    assert "12345" in signals[0].message



def test_compute_image_text_similarity_clip_truncation():
    from unittest.mock import MagicMock
    from core.image.detector import UnivFDDetector
    import torch

    img_bytes = _create_test_image_bytes()
    long_query_text = "This is a very long text description designed to exceed seventy-seven characters and ensure that tokenizer-level truncation is properly requested without slicing " * 3

    mock_detector = MagicMock()
    mock_detector.is_loaded = True
    mock_detector.device = "cpu"

    # Mock processor return
    mock_pixel_values = torch.zeros((1, 3, 224, 224))
    mock_input_ids = torch.zeros((1, 77), dtype=torch.long)
    mock_inputs = MagicMock()
    mock_inputs.pixel_values = mock_pixel_values
    mock_inputs.input_ids = mock_input_ids
    mock_detector.processor.return_value = mock_inputs

    # Mock model features
    mock_detector.model.get_image_features.return_value = torch.ones((1, 768))
    mock_detector.model.get_text_features.return_value = torch.ones((1, 768))

    with patch.object(UnivFDDetector, "get_instance", return_value=mock_detector):
        score, status = compute_image_text_similarity(img_bytes, long_query_text)

        # Verify processor was called with truncation=True and max_length=77
        mock_detector.processor.assert_called_once()
        _, kwargs = mock_detector.processor.call_args
        assert kwargs.get("truncation") is True
        assert kwargs.get("max_length") == 77
        # Verify text was passed in full without character slice
        assert kwargs.get("text") == [long_query_text.strip()]
        assert status == RelationshipStatus.CONSISTENT
