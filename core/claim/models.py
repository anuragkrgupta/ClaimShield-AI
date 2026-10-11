"""
Claim data models and basic consistency checks for ClaimShield AI.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Union, Any


@dataclass
class EvidenceItem:
    """Represents a piece of evidence submitted with a claim."""
    item_id: str
    evidence_type: str  # "IMAGE", "DOCUMENT", "INVOICE", "RECEIPT", "ESTIMATE", etc.
    file_path: Optional[str] = None
    file_bytes: Optional[bytes] = None
    extracted_date: Optional[Union[date, str]] = None
    extracted_amount: Optional[Union[float, int, str]] = None
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Claim:
    """Represents an insurance claim entity with associated evidence."""
    claim_id: str
    claimant_name: Optional[str] = None
    incident_date: Optional[Union[date, str]] = None
    claim_date: Optional[Union[date, str]] = None
    claimed_amount: Optional[Union[float, int, str]] = None
    claim_type: Optional[str] = None  # Generic category (e.g., "Property", "Motor", "Medical", etc.)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
