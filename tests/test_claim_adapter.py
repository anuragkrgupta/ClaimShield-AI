"""
Tests for document-to-evidence adapter and claim analysis orchestration.
"""
import pytest
from datetime import date
from decimal import Decimal
import fitz

from core.types import Signal
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


def test_claim_id_extraction_misleading_headings_rejected():
    """Verify misleading headings are not misidentified as claim IDs and do not cause false mismatches."""
    misleading_headings = [
        "Claim Type: Motor Collision",
        "Claim Details: Front windshield crack",
        "Claim Status: Pending Assessment",
        "Claim Form: Comprehensive",
        "Claim Policy: POL-9988",
    ]

    for heading in misleading_headings:
        doc = ExtractedDocument(
            text=f"Official Form Header\n{heading}\nTotal Amount: $500.00\nDate: 2026-05-12",
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-12"],
            amounts=["$500.00"],
        )

        item = document_to_evidence_item(doc, item_id="DOC-HDG")

        # Must NOT extract ordinary heading as a claim ID
        assert item.metadata.get("claim_id") is None, f"Heading '{heading}' was falsely extracted as claim_id '{item.metadata.get('claim_id')}'"

        # Verify no false-positive CROSS_EVIDENCE_CLAIM_ID_MISMATCH is emitted
        claim = Claim(
            claim_id="CLM-1001",
            incident_date="2026-05-10",
            claim_date="2026-05-15",
            claimed_amount=500.00,
            evidence_items=[item],
        )

        signals = analyze_claim(claim)
        signal_names = [s.name for s in signals]
        assert "CROSS_EVIDENCE_CLAIM_ID_MISMATCH" not in signal_names, f"Heading '{heading}' produced spurious claim ID mismatch!"


def test_claim_id_extraction_valid_explicit_formats():
    """Verify explicit claim-identifier labels are correctly extracted."""
    supported_formats = [
        ("Claim ID: CLM-7788", "CLM-7788"),
        ("Claim Number: CLM-7788", "CLM-7788"),
        ("Claim No: CLM-7788", "CLM-7788"),
        ("Claim No.: CLM-7788", "CLM-7788"),
        ("Claim Reference: CLM-7788", "CLM-7788"),
        ("Claim Ref: CLM-7788", "CLM-7788"),
        ("Claim #CLM-7788", "CLM-7788"),
        ("Claim# CLM-7788", "CLM-7788"),
        ("Claim Num: CLM-7788", "CLM-7788"),
        ("Claim ID# CLM-7788", "CLM-7788"),
        ("Claim ID: 100234", "100234"),
        ("Claim Number: 987654", "987654"),
        ("Claim No: C-4455", "C-4455"),
        ("Claim #99001", "99001"),
    ]

    for text_sample, expected_id in supported_formats:
        doc = ExtractedDocument(
            text=f"Supporting Documentation\n{text_sample}\nDate: 2026-05-12",
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-12"],
        )

        item = document_to_evidence_item(doc, item_id="DOC-VAL")
        assert item.metadata.get("claim_id") == expected_id, f"Failed to extract '{expected_id}' from '{text_sample}'"

        # When evaluated against conflicting claim, correctly flags mismatch
        claim_conflicting = Claim(
            claim_id="CLM-1001",
            incident_date="2026-05-10",
            claim_date="2026-05-15",
            evidence_items=[item],
        )
        signals = analyze_claim(claim_conflicting)
        assert any(s.name == "CROSS_EVIDENCE_CLAIM_ID_MISMATCH" for s in signals)


def test_claim_id_extraction_rejects_unrelated_identifiers():
    """Verify policy numbers, invoice numbers, and unrelated IDs are not mistaken for claim IDs."""
    unrelated_samples = [
        "Policy Number: POL-9988",
        "Policy No: POL-9988",
        "Invoice Number: INV-1234",
        "Receipt ID: REC-5544",
        "Estimate Number: EST-6677",
        "Claim Reference: POL-9988",  # Policy number following Claim Reference
        "Claim Ref: INV-9988",        # Invoice number following Claim Ref
        "Claim Reference: REC-8899",  # Receipt number following Claim Reference
        "Claim Number: POLICY-1234",  # Policy prefix following Claim Number
    ]

    for sample in unrelated_samples:
        doc = ExtractedDocument(
            text=f"Document Header\n{sample}\nDate: 2026-05-12",
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-12"],
        )

        item = document_to_evidence_item(doc, item_id="DOC-UNRELATED")
        assert item.metadata.get("claim_id") is None, f"Unrelated identifier '{sample}' was mistaken for claim_id '{item.metadata.get('claim_id')}'"


def test_claim_id_extraction_ordinary_heading_followed_by_genuine_claim_id():
    """Verify an ordinary heading followed by a genuine claim ID later in the same document extracts the valid ID."""
    headings = [
        "Claim Type: Comprehensive Collision",
        "Claim Details: Driver side door damage",
        "Claim Status: Pending Assessment",
        "Claim Form: Motor Vehicle Loss",
        "Claim Policy: POL-9988",
    ]

    for heading in headings:
        doc = ExtractedDocument(
            text=(
                f"Incident Report\n"
                f"{heading}\n"
                f"Incident Date: 2026-05-10\n"
                f"Claim Number: CLM-7788\n"
                f"Total Claimed: $1,200.00"
            ),
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-10"],
            amounts=["$1,200.00"],
        )

        item = document_to_evidence_item(doc, item_id="DOC-HEAD-VALID")
        assert item.metadata.get("claim_id") == "CLM-7788", (
            f"Failed to extract genuine claim ID 'CLM-7788' when preceded by heading '{heading}'. Got: '{item.metadata.get('claim_id')}'"
        )


def test_claim_id_extraction_rejects_ordinary_words():
    """Verify ordinary words following explicit claim labels without digits or claim markers are rejected."""
    word_samples = [
        "Claim Reference: Pending Assessment",
        "Claim Reference: Under Review",
        "Claim Reference: General Damage",
        "Claim ID: Approved",
        "Claim Number: Unassigned",
        "Claim Ref: Comprehensive",
    ]

    for sample in word_samples:
        doc = ExtractedDocument(
            text=f"Supporting Documentation\n{sample}\nDate: 2026-05-12",
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-12"],
        )
        item = document_to_evidence_item(doc, item_id="DOC-WORD")
        assert item.metadata.get("claim_id") is None, f"Ordinary word in '{sample}' was falsely extracted as claim_id '{item.metadata.get('claim_id')}'"


def test_claim_id_extraction_iterates_past_earlier_false_matches():
    """Verify earlier false matches (words, policy numbers, invoices) do not hide a later valid claim ID."""
    doc = ExtractedDocument(
        text=(
            "Claim Form Summary\n"
            "Claim Reference: Pending Assessment\n"
            "Claim Reference: POL-9988\n"
            "Claim Ref: INV-1234\n"
            "Claim Number: CLM-3344\n"
            "Date: 2026-05-12"
        ),
        metadata=DocumentMetadata(format="PDF"),
        dates=["2026-05-12"],
    )

    item = document_to_evidence_item(doc, item_id="DOC-MULTI-MATCH")
    assert item.metadata.get("claim_id") == "CLM-3344", f"Expected 'CLM-3344' but got '{item.metadata.get('claim_id')}'"


def test_claim_id_extraction_marker_prefix_formats():
    """Verify claim marker formats like 'Claim: CLM-8899' and 'Claim: CLAIM-7766' are extracted."""
    marker_samples = [
        ("Claim: CLM-8899", "CLM-8899"),
        ("Claim - CLM-8899", "CLM-8899"),
        ("Claim: CLAIM-7766", "CLAIM-7766"),
    ]

    for sample, expected in marker_samples:
        doc = ExtractedDocument(
            text=f"Header\n{sample}\nDate: 2026-05-12",
            metadata=DocumentMetadata(format="PDF"),
            dates=["2026-05-12"],
        )
        item = document_to_evidence_item(doc, item_id="DOC-MARKER")
        assert item.metadata.get("claim_id") == expected, f"Failed to extract '{expected}' from '{sample}'"


def test_analyze_claim_hardened_document_signals():
    """Verify analyze_claim handles None, non-iterables, single signals, and normal collections without TypeError."""
    doc = ExtractedDocument(
        text="Sample Document Text",
        metadata=DocumentMetadata(format="PDF"),
    )

    # 1. Test metadata_overrides with None
    item_none = document_to_evidence_item(doc, item_id="D-NONE", metadata_overrides={"document_signals": None})
    claim_none = Claim(claim_id="CLM-100", evidence_items=[item_none])
    signals_none = analyze_claim(claim_none)
    assert isinstance(signals_none, list)

    # 2. Test metadata_overrides with unsupported non-iterable string
    item_str = document_to_evidence_item(doc, item_id="D-STR", metadata_overrides={"document_signals": "not-a-signal-list"})
    claim_str = Claim(claim_id="CLM-100", evidence_items=[item_str])
    signals_str = analyze_claim(claim_str)
    assert isinstance(signals_str, list)

    # 3. Test metadata_overrides with unsupported integer
    item_int = document_to_evidence_item(doc, item_id="D-INT", metadata_overrides={"document_signals": 12345})
    claim_int = Claim(claim_id="CLM-100", evidence_items=[item_int])
    signals_int = analyze_claim(claim_int)
    assert isinstance(signals_int, list)

    # 4. Test metadata_overrides with a single Signal object
    single_signal = Signal(name="CUSTOM_TAMPER_FLAG", severity="MEDIUM", score=50, message="Custom tamper finding")
    item_single = document_to_evidence_item(doc, item_id="D-SIG", metadata_overrides={"document_signals": single_signal})
    claim_single = Claim(claim_id="CLM-100", evidence_items=[item_single])
    signals_single = analyze_claim(claim_single)
    assert any(s.name == "CUSTOM_TAMPER_FLAG" for s in signals_single)
