import pytest
from datetime import date, datetime
from decimal import Decimal

from core.claim.models import Claim, EvidenceItem
from core.claim.consistency import (
    check_date_consistency,
    check_amount_consistency,
    verify_claim_consistency,
)


def test_consistent_claim():
    claim = Claim(
        claim_id="CLM-1001",
        claimant_name="Alice Smith",
        incident_date="2026-05-10",
        claim_date="2026-05-15",
        claimed_amount=1500.00,
        claim_type="Property",
        evidence_items=[
            EvidenceItem(
                item_id="DOC-1",
                evidence_type="INVOICE",
                extracted_date="2026-05-12",
                extracted_amount=1500.00,
                description="Repair Invoice",
            )
        ],
    )
    signals = verify_claim_consistency(claim)
    assert len(signals) == 0


def test_empty_and_minimal_claim():
    # A claim with only an ID and no dates or amounts should not crash and should produce no contradiction signals
    claim = Claim(claim_id="CLM-1002")
    signals = verify_claim_consistency(claim)
    assert len(signals) == 0


def test_date_incident_after_claim_filing():
    claim = Claim(
        claim_id="CLM-1003",
        incident_date="2026-06-20",
        claim_date="2026-06-10",
    )
    signals = check_date_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "DATE_TIMELINE_INCONSISTENT"
    assert signals[0].severity == "HIGH"
    assert "Incident date (2026-06-20) is after the claim filing date (2026-06-10)" in signals[0].message


def test_evidence_date_predates_incident():
    claim = Claim(
        claim_id="CLM-1004",
        incident_date="2026-05-15",
        claim_date="2026-05-20",
        evidence_items=[
            EvidenceItem(
                item_id="INV-001",
                evidence_type="INVOICE",
                extracted_date="2026-05-01",  # 14 days before incident
            )
        ],
    )
    signals = check_date_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "EVIDENCE_PREDATES_INCIDENT"
    assert signals[0].severity == "HIGH"
    assert "predates the reported incident date" in signals[0].message


def test_malformed_dates():
    claim = Claim(
        claim_id="CLM-1005",
        incident_date="not-a-date",
        claim_date="2026/05/20",
        evidence_items=[
            EvidenceItem(
                item_id="EVID-1",
                evidence_type="DOCUMENT",
                extracted_date="invalid-date-string",
            )
        ],
    )
    signals = check_date_consistency(claim)
    names = [s.name for s in signals]
    assert "DATE_FORMAT_INVALID" in names
    assert "EVIDENCE_DATE_INVALID" in names


def test_date_types_date_and_datetime():
    claim = Claim(
        claim_id="CLM-1006",
        incident_date=date(2026, 4, 1),
        claim_date=datetime(2026, 4, 5, 10, 30),
        evidence_items=[
            EvidenceItem(
                item_id="EVID-1",
                evidence_type="RECEIPT",
                extracted_date=date(2026, 4, 2),
            )
        ],
    )
    signals = check_date_consistency(claim)
    assert len(signals) == 0


def test_claimed_amount_exceeds_evidence():
    claim = Claim(
        claim_id="CLM-2001",
        claimed_amount="5000.00",
        evidence_items=[
            EvidenceItem(
                item_id="INV-1",
                evidence_type="INVOICE",
                extracted_amount="3500.00",
            ),
            EvidenceItem(
                item_id="INV-2",
                evidence_type="RECEIPT",
                extracted_amount=500.00,
            ),
        ],
    )
    signals = check_amount_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "AMOUNT_EXCEEDS_SUPPORTING_EVIDENCE"
    assert signals[0].severity == "HIGH"
    assert "Claimed amount (5000.00) exceeds total supporting evidence amount (4000.00) by 1000.00" in signals[0].message


def test_claimed_amount_less_than_evidence():
    claim = Claim(
        claim_id="CLM-2002",
        claimed_amount=2000,
        evidence_items=[
            EvidenceItem(
                item_id="INV-1",
                evidence_type="INVOICE",
                extracted_amount=2500,
            )
        ],
    )
    signals = check_amount_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "AMOUNT_LESS_THAN_SUPPORTING_EVIDENCE"
    assert signals[0].severity == "MEDIUM"
    assert "Claimed amount (2000) is less than total supporting evidence amount (2500) by 500" in signals[0].message


def test_amount_formatting_and_currencies():
    claim = Claim(
        claim_id="CLM-2003",
        claimed_amount="$ 1,250.50",
        evidence_items=[
            EvidenceItem(
                item_id="INV-1",
                evidence_type="INVOICE",
                extracted_amount="€1,250.50",
            )
        ],
    )
    signals = check_amount_consistency(claim)
    assert len(signals) == 0


def test_malformed_and_negative_amounts():
    claim = Claim(
        claim_id="CLM-2004",
        claimed_amount="invalid_currency",
        evidence_items=[
            EvidenceItem(
                item_id="INV-1",
                evidence_type="INVOICE",
                extracted_amount="bad_amt",
            ),
            EvidenceItem(
                item_id="INV-2",
                evidence_type="INVOICE",
                extracted_amount="-50.00",
            ),
        ],
    )
    signals = check_amount_consistency(claim)
    names = [s.name for s in signals]
    assert "AMOUNT_FORMAT_INVALID" in names
    assert "EVIDENCE_AMOUNT_INVALID" in names
    assert "EVIDENCE_AMOUNT_NEGATIVE" in names


def test_negative_claimed_amount():
    claim = Claim(
        claim_id="CLM-2005",
        claimed_amount=-500,
    )
    signals = check_amount_consistency(claim)
    assert len(signals) == 1
    assert signals[0].name == "AMOUNT_NEGATIVE"
    assert signals[0].severity == "HIGH"
