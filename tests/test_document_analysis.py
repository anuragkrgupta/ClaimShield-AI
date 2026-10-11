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


def test_document_synthetic_repetition_anomaly():
    looped_text = "lorem ipsum repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair repair"
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
