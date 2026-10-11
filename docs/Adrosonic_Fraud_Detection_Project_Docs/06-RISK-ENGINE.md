# Risk Engine and Explainability

## Objective

Turn heterogeneous evidence signals into an explainable, defensible fraud-likelihood assessment for human investigators.

---

## Current Implementation Status

* **Implemented (`core/risk.py`):** `calculate_image_authenticity(signals: List[Signal]) -> int`. Currently extracts the UnivFD detection score (or defaults to 100 if no anomaly is flagged).
* **Planned (Phase 6):** Full multi-tier fusion engine integrating Document Authenticity, Claim Consistency, and Overall Fraud Likelihood.

---

## Core Principles

### 1. Distinct Concepts
Do not treat detection outputs as interchangeable:
* **AI-generation likelihood:** The model's probability estimate that an image is synthetic.
* **Image forensic indicators:** Physical or compression artifacts (e.g., Moiré screen patterns, JPEG blockiness).
* **Image Authenticity Score:** Composite confidence that the image is a genuine digital capture.
* **Overall Fraud Likelihood:** Claim-level probability combining image authenticity, document validity, and claim consistency.

**Rule:** High AI-generation likelihood is **evidence**, not legal proof of fraud. Conversely, a high image authenticity score is not a guarantee of genuine claim legitimacy.

### 2. Tiered Evidence Authority
Do not treat every signal as equally reliable:

```text
Deterministic Mismatches (Dates, Amounts)
        = High-confidence, verifiable evidence

Dedicated AI Detector (UnivFD)
        = Primary model signal (advisory likelihood)

Supporting Forensics (Recapture / Metadata)
        = Supporting circumstantial indicators
```

---

## Score Architecture

### 1. Image Authenticity Score [Implemented]
* **Range:** 0 (highly suspicious / synthetic) to 100 (authentic).
* **Current Input:** `UNIVFD_AI_DETECTION` signal.
* **Planned Inputs:** Candidate recapture detection (Moiré / blockiness) and metadata checks.
* *Excluded:* Error Level Analysis (ELA) and reference noise analysis were evaluated and rejected due to false-alarm rates on generic images.

### 2. Document Authenticity Score [Planned — Phase 5/6]
* **Range:** 0 (tampered / fraudulent) to 100 (authentic).
* **Inputs:** OCR field consistency, document metadata tampering, visual layout alterations.

### 3. Claim Consistency Score [Planned — Phase 4/6]
* **Range:** 0 (high discrepancy) to 100 (fully consistent).
* **Inputs (P0):** Incident date vs. document/metadata dates; claimed amount vs. invoice/receipt totals.
* **Inputs (P1):** Claimant name matching across evidence items.

### 4. Overall Fraud Likelihood [Planned — Phase 6]
* **Range:** 0 (low fraud risk) to 100 (high fraud risk).
* **Fusion:** Transparent, weighted policy combining image, document, and consistency scores.
* **Tiers:** `LOW` (< 40), `MEDIUM` (40–69), `HIGH` (>= 70).

---

## Explainability Contract

Every check emits a standardized `Signal` object matching `core/types.py`:

```python
@dataclass
class Signal:
    name: str                      # e.g., "UNIVFD_AI_DETECTION", "DATE_MISMATCH"
    severity: str                  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: int                     # 0-100 authenticity score representation
    message: str                   # Plain-English explanation
    confidence: Optional[float] = None  # Model confidence or synthetic probability
```

### Example Summary Presentation

```text
OVERALL FRAUD LIKELIHOOD — 74% (HIGH)

Primary Findings:
- UNIVFD_AI_DETECTION [HIGH]: AI-generation likelihood: 91.0% (Score: 9/100)
- DOCUMENT_ALTERATION [HIGH]: Modification timestamp does not match original creation.
- AMOUNT_MISMATCH [HIGH]: Claimed amount ($85,000) exceeds supporting invoice ($58,000).

Supporting Findings:
- RECAPTURE_INDICATOR [MEDIUM]: Periodic frequency peak suggests screen photograph.

Recommended Action:
- Secondary manual investigation recommended before claim settlement.
```

---

## Human-in-the-Loop & Language Safety

The output is a decision-support indicator for claim adjusters, **not a legal determination**.

* **Mandatory language:** "High fraud likelihood", "Secondary review recommended", "Potential manipulation indicator detected", "Inconsistency flagged".
* **Prohibited language:** "100% FRAUD", "Fraud committed", "The claimant is guilty".
* Model-derived probabilities must always be presented as model confidence, not empirical certainty.

---

## Centralized Configuration Policy

Weights, score tiers, and threshold values must be managed in a centralized configuration file (`config.py`) once multi-tier fusion is built. Avoid scattering arbitrary heuristic numbers across detector modules.
