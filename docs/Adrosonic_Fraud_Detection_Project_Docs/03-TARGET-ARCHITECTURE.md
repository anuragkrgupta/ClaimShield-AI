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
   Image Analysis          Document Analysis
          |                       |
   +------+-------+        +------+-------+
   |      |       |        |      |       |
  AI    ELA    Recapture   OCR  Metadata  Tampering
   |      |       |        |      |       |
   +------+-------+        +------+-------+
          |                       |
          v                       v
   Image Evidence          Document Evidence
          |                       |
          +-----------+-----------+
                      |
                      v
             Claim Consistency
                      |
                      v
               Identity Check
                      |
                      v
                Risk Engine
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
      Image        Document      Overall
      Score         Score        Fraud Risk
                      |
                      v
               Explainable UI
```

## Proposed project structure

```text
fraud-detection/
├── app.py
├── config.py
├── requirements.txt
│
├── core/
│   ├── pipeline.py
│   ├── risk.py
│   ├── types.py
│   │
│   ├── image/
│   │   ├── detector.py
│   │   ├── preprocess.py
│   │   └── forensics.py
│   │
│   ├── document/
│   │   ├── ocr.py
│   │   ├── tampering.py
│   │   ├── metadata.py
│   │   └── fields.py
│   │
│   ├── identity/
│   │   └── face.py
│   │
│   └── claim/
│       ├── parser.py
│       └── consistency.py
│
├── models/
├── data/
├── ui/
│   ├── pages.py
│   ├── components.py
│   └── style.py
│
└── tests/
```

## Pipeline contract

Every detector should return a standardized signal.

Conceptually:

```python
Signal(
    category="image_ai_detection",
    severity="FAIL",
    score=91,
    confidence=0.91,
    message="High probability of synthetic image",
    detail={...}
)
```

The exact existing `Signal` type should be reused where practical rather than introducing a second incompatible signal system.

## Detector interface

The AI image detector should behave approximately like:

```python
result = detect_image(image)

{
    "label": "AI_GENERATED",
    "confidence": 0.91,
    "authenticity_score": 9,
    "reason": "High probability of synthetic content"
}
```

The model implementation must remain replaceable.

## Data model

Minimal claim model:

```python
claim = {
    "claim_id": "...",
    "claimant_name": "...",
    "claim_date": "...",
    "claim_type": "Vehicle Accident",
    "claimed_amount": 85000,
    "images": [],
    "documents": []
}
```

Keep it simple for the hackathon.

## Evidence categories

### Image evidence
- AI/deepfake classifier
- ELA
- noise
- recapture
- compression/metadata
- suspicious regions

### Document evidence
- OCR
- metadata
- font/layout indicators where available
- field consistency
- document image forensics

### Claim evidence
- name
- dates
- amounts
- identifiers
- image/document consistency

### Identity evidence
- face similarity
- mismatch
- optional morphing indicator

## Human-in-the-loop

The output should recommend investigation, not pretend to be an absolute legal decision.

Preferred language:
- "High fraud likelihood"
- "Secondary review recommended"
- "Suspicious indicator detected"

Avoid:
- "This person committed fraud."
- "This claim is definitely fraudulent."
