"""
Tests for document-to-evidence adapter and claim analysis orchestration.
"""
import pytest
from datetime import date
from decimal import Decimal
import fitz

from core.claim.models import Claim, EvidenceItem
from core.document.extractor import (
    DocumentMetadata,
    ExtractedDocument,
)
from core.claim.adapter import (
    document_to_evidence_item,
    document_file_to_evidence_item,
    resolve_document_date,
    resolve_document_amount,
    analyze_claim,
)


def _create_minimal_pdf_bytes(text: str = "Invoice #INV-5544\nDate: 2026-05-12\nTotal: $1,250.00") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_document_to_evidence_item_valid_mapping():
    doc = ExtractedDocument(
        text="Official Invoice #INV-1234\nDate: 2026-05-12\nTotal: $1,500.00",
        metadata=DocumentMetadata(
            format="PDF",
            page_count=1,
            producer="ReportLab PDF Library - version 3.5",
            creation_date="D:20260512100000",
            mod_date="D:20260512100000",
        ),
        dates=["2026-05-12"],
        amounts=["$1,500.00"],
        identifiers=["INV-1234"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-101", evidence_type="INVOICE")

    assert item.item_id == "DOC-101"
    assert item.evidence_type == "INVOICE"
    assert item.extracted_date == "2026-05-12"
    assert item.extracted_amount == "$1,500.00"
    assert "Official Invoice" in item.description
    assert item.metadata["identifiers"] == ["INV-1234"]
    assert item.metadata["candidate_dates"] == ["2026-05-12"]
    assert item.metadata["candidate_amounts"] == ["$1,500.00"]
    assert item.metadata["has_ambiguous_dates"] is False
    assert item.metadata["has_ambiguous_amounts"] is False
    assert item.metadata["document_format"] == "PDF"
    assert len(item.metadata["document_signals"]) == 0  # Clean document -> no tampering


def test_document_to_evidence_item_missing_fields():
    doc = ExtractedDocument(
        text="Scanned image without clear fields",
        metadata=DocumentMetadata(format="IMAGE"),
        dates=[],
        amounts=[],
        identifiers=[],
    )

    item = document_to_evidence_item(doc, item_id="DOC-102")

    assert item.item_id == "DOC-102"
    assert item.extracted_date is None
    assert item.extracted_amount is None
    assert item.metadata["identifiers"] == []
    assert item.metadata["candidate_dates"] == []
    assert item.metadata["candidate_amounts"] == []
    assert item.metadata["has_ambiguous_dates"] is False
    assert item.metadata["has_ambiguous_amounts"] is False


def test_document_to_evidence_item_multiple_candidate_dates():
    # Multiple distinct dates (e.g. invoice date vs due date) -> must NOT arbitrarily choose
    doc = ExtractedDocument(
        text="Invoice Date: 2026-05-10\nPayment Due: 2026-05-25",
        metadata=DocumentMetadata(format="PDF"),
        dates=["2026-05-10", "2026-05-25"],
        amounts=["$500.00"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-103")

    # Safe behavior: extracted_date is None rather than guessing one
    assert item.extracted_date is None
    assert item.metadata["candidate_dates"] == ["2026-05-10", "2026-05-25"]
    assert item.metadata["has_ambiguous_dates"] is True
    # Amount was unique, so it is preserved
    assert item.extracted_amount == "$500.00"


def test_document_to_evidence_item_identical_parsed_dates():
    # Same date formatted in different ways in the document -> single unique date
    doc = ExtractedDocument(
        text="Date: 2026-05-10\nBilled: 10-05-2026",
        metadata=DocumentMetadata(format="PDF"),
        dates=["2026-05-10", "10-05-2026"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-104")

    assert item.extracted_date == "2026-05-10"
    assert item.metadata["has_ambiguous_dates"] is False


def test_document_to_evidence_item_multiple_candidate_amounts():
    # Multiple distinct amounts (e.g. line item vs total) -> must NOT arbitrarily choose
    doc = ExtractedDocument(
        text="Labor: $250.00\nParts: $1,000.00\nTotal: $1,250.00",
        metadata=DocumentMetadata(format="PDF"),
        dates=["2026-05-10"],
        amounts=["$250.00", "$1,000.00", "$1,250.00"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-105")

    # Safe behavior: extracted_amount is None rather than guessing
    assert item.extracted_amount is None
    assert item.metadata["candidate_amounts"] == ["$250.00", "$1,000.00", "$1,250.00"]
    assert item.metadata["has_ambiguous_amounts"] is True
    assert item.extracted_date == "2026-05-10"


def test_document_to_evidence_item_identical_parsed_amounts():
    # Multiple amount strings resolving to identical Decimal -> single unique amount
    doc = ExtractedDocument(
        text="Item: $1250.00\nTotal: 1,250.00",
        metadata=DocumentMetadata(format="PDF"),
        amounts=["$1250.00", "Total: 1,250.00"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-106")

    assert item.extracted_amount == "$1250.00"
    assert item.metadata["has_ambiguous_amounts"] is False


def test_document_to_evidence_item_identifiers_and_claim_id():
    doc = ExtractedDocument(
        text="Supporting Bill\nPolicy No: POL-7788\nRelated Claim #CLM-4321\nInvoice Ref: INV-9900",
        metadata=DocumentMetadata(format="PDF"),
        identifiers=["POL-7788", "CLM-4321", "INV-9900"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-107")

    assert "POL-7788" in item.metadata["identifiers"]
    assert "INV-9900" in item.metadata["identifiers"]
    assert item.metadata["claim_id"] == "CLM-4321"


def test_document_file_to_evidence_item_pdf():
    pdf_bytes = _create_minimal_pdf_bytes("Medical Receipt #MED-9988\nDate: 2026-04-15\nTotal: $350.00")
    item, ok = document_file_to_evidence_item(pdf_bytes, filename="receipt.pdf", item_id="MED-1", evidence_type="RECEIPT")

    assert ok is True
    assert item is not None
    assert item.item_id == "MED-1"
    assert item.evidence_type == "RECEIPT"
    assert item.extracted_date == "2026-04-15"
    assert any("350" in a for a in item.metadata["candidate_amounts"])
    assert "MED-9988" in item.metadata["identifiers"]


def test_document_file_to_evidence_item_empty_bytes():
    item, ok = document_file_to_evidence_item(b"", filename="empty.pdf")
    assert ok is False
    assert item is None


def test_analyze_claim_end_to_end_consistent():
    claim = Claim(
        claim_id="CLM-1001",
        claimant_name="Alice Smith",
        incident_date="2026-05-10",
        claim_date="2026-05-15",
        claimed_amount=1500.00,
        claim_type="Property",
    )

    doc = ExtractedDocument(
        text="Invoice #INV-001\nDate: 2026-05-12\nTotal: $1,500.00\nClaim #CLM-1001",
        metadata=DocumentMetadata(
            format="PDF",
            producer="ReportLab PDF Library",
            creation_date="D:20260512100000",
            mod_date="D:20260512100000",
        ),
        dates=["2026-05-12"],
        amounts=["$1,500.00"],
        identifiers=["INV-001", "CLM-1001"],
    )

    evidence_item = document_to_evidence_item(doc, item_id="DOC-1", evidence_type="INVOICE")
    claim.evidence_items.append(evidence_item)

    signals = analyze_claim(claim)

    # Clean claim and consistent document evidence -> zero contradiction signals
    assert len(signals) == 0


def test_analyze_claim_end_to_end_with_discrepancies():
    claim = Claim(
        claim_id="CLM-2001",
        claimant_name="Bob Jones",
        incident_date="2026-05-15",
        claim_date="2026-05-20",
        claimed_amount=5000.00,  # Exceeds supporting evidence ($1,500.00)
    )

    # Document exhibits tampering (Photoshop) + date predating incident + conflicting claim ID
    doc = ExtractedDocument(
        text="Repair Quote\nDate: 2026-05-01\nTotal: $1,500.00\nClaim #CLM-9999",
        metadata=DocumentMetadata(
            format="PDF",
            producer="Adobe Photoshop 24.0",
        ),
        dates=["2026-05-01"],
        amounts=["$1,500.00"],
        identifiers=["CLM-9999"],
    )

    evidence_item = document_to_evidence_item(doc, item_id="DOC-1", evidence_type="INVOICE")
    claim.evidence_items.append(evidence_item)

    signals = analyze_claim(claim)
    signal_names = [s.name for s in signals]

    # Verify all subsystems emitted their appropriate signals through the orchestration function
    assert "DOC_EDITING_SOFTWARE_DETECTED" in signal_names
    assert "EVIDENCE_PREDATES_INCIDENT" in signal_names
    assert "AMOUNT_EXCEEDS_SUPPORTING_EVIDENCE" in signal_names
    assert "CROSS_EVIDENCE_CLAIM_ID_MISMATCH" in signal_names


def test_analyze_claim_with_multiple_candidate_dates_and_amounts():
    claim = Claim(
        claim_id="CLM-3001",
        incident_date="2026-05-10",
        claim_date="2026-05-20",
        claimed_amount=1000.00,
    )

    # Document has multiple dates and multiple amounts
    doc = ExtractedDocument(
        text="Estimate\nOption A Date: 2026-05-12\nOption B Date: 2026-05-18\nOption A: $800.00\nOption B: $1,200.00",
        metadata=DocumentMetadata(format="PDF"),
        dates=["2026-05-12", "2026-05-18"],
        amounts=["$800.00", "$1,200.00"],
    )

    evidence_item = document_to_evidence_item(doc, item_id="DOC-1", evidence_type="ESTIMATE")
    claim.evidence_items.append(evidence_item)

    signals = analyze_claim(claim)
    signal_names = [s.name for s in signals]

    # Multiple candidates were flagged as informational signals without false contradictions
    assert "DOCUMENT_MULTIPLE_DATES_DETECTED" in signal_names
    assert "DOCUMENT_MULTIPLE_AMOUNTS_DETECTED" in signal_names
    # And because date and amount were safely set to None, no false amount mismatch was triggered
    assert "AMOUNT_EXCEEDS_SUPPORTING_EVIDENCE" not in signal_names
    assert "AMOUNT_LESS_THAN_SUPPORTING_EVIDENCE" not in signal_names
