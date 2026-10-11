# Target Architecture

## Design principle

One application, one clear pipeline.

Avoid unnecessary distributed architecture.

## High-level flow

```text
                    CLAIM
                      |
          +-----------+-----------+
          |                       |
       IMAGES                 DOCUMENTS
          |                       |
          v                       v
   Image Analysis          Document Analysis (Planned)
          |                       |
   +------+-------+        +------+-------+
   |              |        |      |       |
  AI          Recapture   OCR  Metadata  Tampering
(UnivFD)     (Candidate)   |      |       |
   |              |        +------+-------+
   +------+-------+               |
          |                       v
          v                Document Evidence
   Image Evidence                 |
          |                       |
          +-----------+-----------+
                      |
                      v
             Claim Consistency (Planned)
                      |
                      v
               Identity Check (Bonus)
                      |
                      v
                Risk Engine (Image active, multi-tier planned)
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
      Image        Document      Overall
      Score         Score        Fraud Risk
   (Active)       (Planned)      (Planned)
                      |
                      v
               Explainable UI
```

## Project structure

### 1. Current Implemented Structure (Phase 2 State)

```text
ClaimShield-AI/
├── app.py                      # Streamlit UI (Single-image UnivFD analysis)
├── requirements.txt            # Project dependencies
├── fc_weights.pth              # UnivFD linear head weights
├── validate_phase2.py          # Empirical model validation script
├── core/
│   ├── types.py                # Signal dataclass contract
│   ├── risk.py                 # calculate_image_authenticity()
│   └── image/
│       └── detector.py         # UnivFDDetector, analyze_image_univfd()
├── tests/
│   └── test_pipeline.py        # Automated unit tests with mocks
└── VerifAI_Ref/                # Read-only reference repository
```

### 2. Target Project Structure (Planned Phases)

```text
ClaimShield-AI/
├── app.py                      # Streamlit UI entry point
├── config.py                   # Centralized thresholds & configuration
├── requirements.txt
├── fc_weights.pth
├── core/
│   ├── types.py                # Shared signal and claim models
│   ├── risk.py                 # Multi-tier risk engine
│   │
│   ├── image/
│   │   ├── detector.py         # AI image detection (UnivFD)
│   │   └── forensics.py        # Candidate supporting forensics (Recapture)
│   │
│   ├── document/               # (Planned)
│   │   ├── ocr.py
│   │   ├── tampering.py
│   │   ├── metadata.py
│   │   └── fields.py
│   │
│   ├── claim/                  # (Planned)
│   │   ├── model.py            # Claim data structures
│   │   └── consistency.py      # Basic & advanced consistency checks
│   │
│   └── identity/               # (Bonus)
│       └── face.py
│
└── tests/
    └── test_pipeline.py
```

## Pipeline contract

Every detector returns a standardized signal matching `core/types.py`:

```python
@dataclass
class Signal:
    """Represents a discrete piece of evidence found during analysis."""
    name: str                      # e.g., "UNIVFD_AI_DETECTION"
    severity: str                  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: int                     # 0-100 authenticity score representation
    message: str                   # Plain-English explanation
    confidence: Optional[float] = None  # Model confidence or synthetic probability
```

Severity conventions in use:
* `"HIGH"`: Indicates high synthetic probability / strong indicator of manipulation.
* `"LOW"`: Indicates high authenticity confidence / no anomalies found.
* `"MEDIUM"`, `"CRITICAL"`: Reserved for intermediate or definitive indicators.

## Detector interface

The implemented image detector in `core/image/detector.py` provides:

```python
signal, success = analyze_image_univfd(image_bytes)
```

Where:
* `image_bytes`: Raw binary bytes of uploaded image.
* Returns `Tuple[Optional[Signal], bool]`:
  * If successful, returns `(signal, True)` where `signal.score` represents Image Authenticity (0–100, where higher is more authentic).
  * If inference fails or model weights cannot be loaded, returns `(None, False)` gracefully without crashing.

The underlying model is encapsulated inside `UnivFDDetector` (singleton pattern with thread safety) so alternative detectors can be substituted behind the same functional interface.

## Data model

Minimal claim model (Planned for Claim Layer):

```python
claim = {
    "claim_id": "...",
    "claimant_name": "...",
    "claim_date": "...",
    "claim_type": "Vehicle Accident",  # Demo scenario
    "claimed_amount": 85000,
    "images": [],
    "documents": []
}
```

Keep the data structures simple and deterministic.

## Evidence categories

### Image evidence
* **AI/deepfake classifier:** UnivFD (Implemented — primary image signal).
* **Recapture detection:** Proposed candidate supporting forensic check (Moiré, JPEG-blockiness) — *Awaiting implementation and validation*.
* **Compression & metadata:** Basic EXIF/format metadata — *Planned*.
* *Note:* Error Level Analysis (ELA) and reference noise analysis were evaluated and **excluded** from the generic image pipeline due to high false-positive rates on natural images.

### Document evidence (Planned)
* OCR text extraction.
* File metadata inspection.
* Visual/layout tampering indicators.
* Cross-field value consistency.

### Claim evidence (Planned)
* Name matching across items.
* Incident date vs document/metadata dates.
* Claimed amount vs invoice/estimate amounts.
* Identifier validation.

### Identity evidence (Bonus)
* Face similarity comparison between ID document and selfie.
* Morphing indicators.

## Human-in-the-loop

The output should recommend investigation, not pretend to be an absolute legal decision.

Preferred language:
- "High fraud likelihood"
- "Secondary review recommended"
- "Suspicious indicator detected"

Avoid:
- "This person committed fraud."
- "This claim is definitely fraudulent."
