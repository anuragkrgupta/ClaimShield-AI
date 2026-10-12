"""
Deterministic consistency checks for claim dates and amounts.
"""
from datetime import date, datetime
from typing import Any, List, Optional, Tuple, Union
from decimal import Decimal, InvalidOperation

from core.types import Signal
from core.claim.models import Claim, EvidenceItem


def _parse_date(val: Any) -> Tuple[Optional[date], bool, bool]:
    """
    Attempts to parse a value into a datetime.date object.
    Returns (parsed_date, is_valid, is_ambiguous).
    If val is None, returns (None, True, False) - meaning not provided, but not malformed.
    If val is invalid string or unsupported type, returns (None, False, False).
    If a slash-separated date like MM/DD/YYYY vs DD/MM/YYYY can validly mean two different dates,
    returns (None, True, True) so ambiguity is flagged without assuming an arbitrary date.
    """
    if val is None:
        return None, True, False
    if isinstance(val, datetime):
        return val.date(), True, False
    if isinstance(val, date):
        return val, True, False
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None, True, False

        # Check for slash-separated ambiguous dates (e.g. 03/04/2026 vs 04/03/2026)
        # Patterns with 2-digit day and month separated by slashes: XX/YY/ZZZZ
        slash_parts = cleaned.split("/")
        if len(slash_parts) == 3 and len(slash_parts[2]) == 4:
            p1, p2, p3 = slash_parts
            # Require strict ASCII digits [0-9]
            if p1.isascii() and p1.isdigit() and p2.isascii() and p2.isdigit() and p3.isascii() and p3.isdigit():
                try:
                    d1, d2 = int(p1), int(p2)
                    # If both parts are in range 1-12 and distinct, it could be either MM/DD/YYYY or DD/MM/YYYY
                    if 1 <= d1 <= 12 and 1 <= d2 <= 12 and d1 != d2:
                        return None, True, True
                except (ValueError, OverflowError):
                    return None, False, False


        # Try common date formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned, fmt).date(), True, False
            except ValueError:
                continue
        return None, False, False
    return None, False, False


def _parse_amount(val: Any) -> Tuple[Optional[Decimal], bool]:
    """
    Attempts to parse a value into a Decimal monetary amount.
    Returns (parsed_amount, is_valid).
    If val is None, returns (None, True).
    If val cannot be parsed as a finite numeric monetary value, returns (None, False).
    Rejects non-finite values (NaN, Infinity, -Infinity).
    """
    if val is None:
        return None, True
    if isinstance(val, (int, float)):
        try:
            dec = Decimal(str(val))
            if not dec.is_finite():
                return None, False
            return dec, True
        except (InvalidOperation, TypeError):
            return None, False
    if isinstance(val, Decimal):
        if not val.is_finite():
            return None, False
        return val, True
    if isinstance(val, str):
        cleaned = val.strip().replace("$", "").replace("€", "").replace("£", "").replace("₹", "").replace(",", "")
        if not cleaned:
            return None, True
        try:
            dec = Decimal(cleaned)
            if not dec.is_finite():
                return None, False
            return dec, True
        except InvalidOperation:
            return None, False
    return None, False


def check_date_consistency(claim: Claim) -> List[Signal]:
    """
    Checks deterministic date consistency for a claim:
    1. Validates format of incident_date and claim_date.
    2. Flags ambiguous slash-separated dates (e.g. 03/04/2026) as low-severity findings.
    3. Checks if incident_date > claim_date (an incident cannot happen after the claim was filed).
    4. Compares incident_date against extracted dates in evidence items (e.g. invoice/evidence dated before the incident).
    """
    signals: List[Signal] = []

    inc_date, inc_valid, inc_ambiguous = _parse_date(claim.incident_date)
    if inc_ambiguous:
        signals.append(Signal(
            name="DATE_FORMAT_AMBIGUOUS",
            severity="LOW",
            score=70,
            message=(
                f"Incident date '{claim.incident_date}' is ambiguous (could represent "
                f"MM/DD/YYYY or DD/MM/YYYY). Awaiting clarification."
            )
        ))
    elif not inc_valid:
        signals.append(Signal(
            name="DATE_FORMAT_INVALID",
            severity="MEDIUM",
            score=50,
            message=f"Incident date '{claim.incident_date}' is malformed or in an unrecognized format."
        ))

    claim_date, claim_valid, claim_ambiguous = _parse_date(claim.claim_date)
    if claim_ambiguous:
        signals.append(Signal(
            name="DATE_FORMAT_AMBIGUOUS",
            severity="LOW",
            score=70,
            message=(
                f"Claim submission date '{claim.claim_date}' is ambiguous (could represent "
                f"MM/DD/YYYY or DD/MM/YYYY). Awaiting clarification."
            )
        ))
    elif not claim_valid:
        signals.append(Signal(
            name="DATE_FORMAT_INVALID",
            severity="MEDIUM",
            score=50,
            message=f"Claim submission date '{claim.claim_date}' is malformed or in an unrecognized format."
        ))

    # Check incident vs claim filing date
    if inc_valid and claim_valid and not inc_ambiguous and not claim_ambiguous and inc_date is not None and claim_date is not None:
        if inc_date > claim_date:
            signals.append(Signal(
                name="DATE_TIMELINE_INCONSISTENT",
                severity="HIGH",
                score=30,
                message=(
                    f"Incident date ({inc_date.isoformat()}) is after the claim filing date "
                    f"({claim_date.isoformat()})."
                )
            ))

    # Check evidence items
    for item in claim.evidence_items:
        item_date, item_date_valid, item_ambiguous = _parse_date(item.extracted_date)
        if item_ambiguous:
            signals.append(Signal(
                name="EVIDENCE_DATE_AMBIGUOUS",
                severity="LOW",
                score=70,
                message=(
                    f"Evidence '{item.item_id}' extracted date '{item.extracted_date}' is ambiguous "
                    f"(could represent MM/DD/YYYY or DD/MM/YYYY)."
                )
            ))
            continue

        if not item_date_valid:
            signals.append(Signal(
                name="EVIDENCE_DATE_INVALID",
                severity="LOW",
                score=70,
                message=f"Evidence '{item.item_id}' has malformed extracted date '{item.extracted_date}'."
            ))
            continue

        if inc_valid and not inc_ambiguous and inc_date is not None and item_date is not None:
            # Evidence dated prior to incident (e.g. repair invoice predates the accident)
            if item_date < inc_date:
                signals.append(Signal(
                    name="EVIDENCE_PREDATES_INCIDENT",
                    severity="HIGH",
                    score=30,
                    message=(
                        f"Evidence item '{item.item_id}' date ({item_date.isoformat()}) "
                        f"predates the reported incident date ({inc_date.isoformat()})."
                    )
                ))

    return signals


def check_amount_consistency(claim: Claim) -> List[Signal]:
    """
    Checks deterministic amount consistency for a claim:
    1. Validates format and non-negativity of claimed_amount.
    2. Validates format of extracted evidence amounts.
    3. If financial evidence items exist (e.g., invoices/estimates), compares claimed_amount
       against the evidence amounts.
       - If claimed_amount exceeds total invoice amounts by a significant margin.
       - If claimed_amount is strictly less than total invoiced amounts (informational / medium discrepancy).
    """
    signals: List[Signal] = []

    claimed_amt, claimed_valid = _parse_amount(claim.claimed_amount)
    if not claimed_valid:
        signals.append(Signal(
            name="AMOUNT_FORMAT_INVALID",
            severity="MEDIUM",
            score=50,
            message=f"Claimed amount '{claim.claimed_amount}' is malformed or non-numeric."
        ))

    if claimed_amt is not None and claimed_amt < 0:
        signals.append(Signal(
            name="AMOUNT_NEGATIVE",
            severity="HIGH",
            score=20,
            message=f"Claimed amount cannot be negative: {claimed_amt}."
        ))

    # Examine evidence items
    total_evidence_amount = Decimal("0")
    has_evidence_amount = False

    for item in claim.evidence_items:
        item_amt, item_amt_valid = _parse_amount(item.extracted_amount)
        if not item_amt_valid:
            signals.append(Signal(
                name="EVIDENCE_AMOUNT_INVALID",
                severity="LOW",
                score=70,
                message=f"Evidence item '{item.item_id}' has malformed amount '{item.extracted_amount}'."
            ))
            continue

        if item_amt is not None:
            if item_amt < 0:
                signals.append(Signal(
                    name="EVIDENCE_AMOUNT_NEGATIVE",
                    severity="HIGH",
                    score=20,
                    message=f"Evidence item '{item.item_id}' has negative amount: {item_amt}."
                ))
            total_evidence_amount += item_amt
            has_evidence_amount = True

    # Compare claimed amount vs evidence total
    if claimed_amt is not None and has_evidence_amount:
        if claimed_amt > total_evidence_amount:
            discrepancy = claimed_amt - total_evidence_amount
            signals.append(Signal(
                name="AMOUNT_EXCEEDS_SUPPORTING_EVIDENCE",
                severity="HIGH",
                score=40,
                message=(
                    f"Claimed amount ({claimed_amt}) exceeds total supporting evidence "
                    f"amount ({total_evidence_amount}) by {discrepancy}."
                )
            ))
        elif claimed_amt < total_evidence_amount:
            discrepancy = total_evidence_amount - claimed_amt
            signals.append(Signal(
                name="AMOUNT_LESS_THAN_SUPPORTING_EVIDENCE",
                severity="MEDIUM",
                score=60,
                message=(
                    f"Claimed amount ({claimed_amt}) is less than total supporting evidence "
                    f"amount ({total_evidence_amount}) by {discrepancy}."
                )
            ))

    return signals


def verify_claim_consistency(claim: Claim) -> List[Signal]:
    """
    Runs all basic P0 consistency checks on the given claim.
    Returns a consolidated list of explainable Signal objects.
    """
    signals: List[Signal] = []
    signals.extend(check_date_consistency(claim))
    signals.extend(check_amount_consistency(claim))
    return signals
