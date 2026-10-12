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


def test_ambiguous_slash_separated_date():
    # 03/04/2026 can be either March 4 or April 3 -> should emit DATE_FORMAT_AMBIGUOUS (LOW severity)
    claim = Claim(
        claim_id="CLM-3001",
        incident_date="03/04/2026",
        claim_date="2026-05-01",
        evidence_items=[
            EvidenceItem(
                item_id="DOC-1",
                evidence_type="INVOICE",
                extracted_date="05/06/2026",  # May 6 or June 5 -> ambiguous
            )
        ]
    )
    signals = check_date_consistency(claim)
    names = [s.name for s in signals]
    assert "DATE_FORMAT_AMBIGUOUS" in names
    assert "EVIDENCE_DATE_AMBIGUOUS" in names
    ambig_signal = next(s for s in signals if s.name == "DATE_FORMAT_AMBIGUOUS")
    assert ambig_signal.severity == "LOW"
    assert "ambiguous" in ambig_signal.message.lower()


def test_unambiguous_slash_separated_date():
    # 25/04/2026 has day 25 (> 12), so only DD/MM/YYYY is valid -> unambiguous
    claim = Claim(
        claim_id="CLM-3002",
        incident_date="25/04/2026",
        claim_date="2026-05-01",
    )
    signals = check_date_consistency(claim)
    # Should be parsed cleanly with no ambiguity or invalid signals
    assert len(signals) == 0


def test_unambiguous_iso_date():
    # 2026-03-04 is standard ISO unambiguous format
    claim = Claim(
        claim_id="CLM-3003",
        incident_date="2026-03-04",
        claim_date="2026-04-01",
    )
    signals = check_date_consistency(claim)
    assert len(signals) == 0


def test_unicode_digit_date_handling():
    # Non-ASCII digits like Arabic-Indic or Persian digits should produce DATE_FORMAT_INVALID rather than unhandled exception
    claim = Claim(
        claim_id="CLM-3004",
        incident_date="١٢/٠٤/٢٠٢٦",  # Unicode arabic-indic digits
        claim_date="2026-05-01",
    )
    signals = check_date_consistency(claim)
    assert any(s.name == "DATE_FORMAT_INVALID" for s in signals)



def test_non_finite_amounts_rejected():
    import math

    # Test string representations: 'NaN', 'Infinity', '-Infinity'
    claim_str_nan = Claim(claim_id="CLM-4001", claimed_amount="NaN")
    signals = check_amount_consistency(claim_str_nan)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    claim_str_inf = Claim(claim_id="CLM-4002", claimed_amount="Infinity")
    signals = check_amount_consistency(claim_str_inf)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    claim_str_neginf = Claim(claim_id="CLM-4003", claimed_amount="-Infinity")
    signals = check_amount_consistency(claim_str_neginf)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    # Test Decimal object inputs
    claim_dec_nan = Claim(claim_id="CLM-4004", claimed_amount=Decimal("NaN"))
    signals = check_amount_consistency(claim_dec_nan)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    claim_dec_inf = Claim(claim_id="CLM-4005", claimed_amount=Decimal("Infinity"))
    signals = check_amount_consistency(claim_dec_inf)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    claim_dec_neginf = Claim(claim_id="CLM-4006", claimed_amount=Decimal("-Infinity"))
    signals = check_amount_consistency(claim_dec_neginf)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    # Test floating-point inf and nan
    claim_float_nan = Claim(claim_id="CLM-4007", claimed_amount=float("nan"))
    signals = check_amount_consistency(claim_float_nan)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    claim_float_inf = Claim(claim_id="CLM-4008", claimed_amount=float("inf"))
    signals = check_amount_consistency(claim_float_inf)
    assert any(s.name == "AMOUNT_FORMAT_INVALID" for s in signals)

    # Test non-finite in evidence items
    claim_evidence_nan = Claim(
        claim_id="CLM-4009",
        claimed_amount=100.0,
        evidence_items=[
            EvidenceItem(
                item_id="EV-1",
                evidence_type="INVOICE",
                extracted_amount="NaN",
            )
        ]
    )
    signals = check_amount_consistency(claim_evidence_nan)
    assert any(s.name == "EVIDENCE_AMOUNT_INVALID" for s in signals)
