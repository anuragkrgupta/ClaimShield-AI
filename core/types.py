from dataclasses import dataclass
from typing import Optional

@dataclass
class Signal:
    """Represents a discrete piece of evidence found during analysis."""
    name: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: int     # 0-100 representation if applicable
    message: str
    confidence: Optional[float] = None
