# UI and 10-Minute Demo Plan

## UI goal

An evaluator should understand the system within seconds.

The UI should prioritize:
1. risk;
2. evidence;
3. explanation.

## Suggested navigation

```text
Dashboard
Claims
New Claim
Analysis Results
Evidence Details
```

For a 24-hour prototype, a single-page or small multi-page Streamlit app is sufficient.

> **Current Implementation Status:** `app.py` currently implements a single-image inspection interface running UnivFD inference, rendering the image preview, synthetic likelihood/confidence, Image Authenticity Score, and plain-English reasons. The full multi-evidence claim workflow described below is the target design planned for Phase 7.

## Target Claim Submission Workflow (Phase 7 Design)

Show:

```text
Claim ID
Claimant
Claim type
Claimed amount

Upload:
[ Accident / Damage images ]
[ Claim documents / invoices ]
[ ID / selfie (Optional bonus) ]
```

Button:

`Analyze Claim`

## Results Dashboard

Top:

```text
OVERALL FRAUD LIKELIHOOD

        74 / 100
        HIGH
```

Then:

```text
Image Authenticity       21 / 100
Document Authenticity    63 / 100
Claim Consistency        38 / 100
Identity                  MATCH
```

## Reasons

```text
Why was this claim flagged?

1. AI-generated image probability is high (UnivFD).
2. Document alteration indicator detected (Metadata modification).
3. Claim amount differs from supporting invoice ($85k claimed vs $58k invoice).
4. Image metadata is inconsistent with the claimed incident timeline.
```

## Evidence details

For an image:
- original image;
- classification and synthetic probability;
- model confidence;
- candidate recapture / metadata indicators (if active);
- *(Note: ELA is excluded due to unreliability on generic images; heatmaps are optional P2 polish).*

For a document:
- preview;
- OCR;
- suspicious fields;
- reasons;
- metadata.

## Demo script

### Minute 0–1 — Problem

Explain:
- digital claims contain multiple evidence types;
- generative AI increases manipulation risk.

### Minute 1–3 — Clean claim

Upload genuine sample.

Show:
- low risk;
- image score;
- document score;
- explanation.

### Minute 3–6 — Fraudulent claim

Upload manipulated/AI-generated image and tampered document.

Show:
- AI detector;
- forensic evidence;
- document flags;
- claim inconsistencies.

### Minute 6–7 — Risk engine

Explain:

```text
Individual evidence
       ↓
Evidence fusion
       ↓
Risk
```

### Minute 7–8 — Identity bonus

Show:
- ID face;
- selfie;
- match/mismatch.

### Minute 8–9 — Architecture

Show:

```text
Upload
 ↓
Detection
 ↓
Evidence
 ↓
Risk
 ↓
Explainability
```

### Minute 9–10 — Impact

Explain:
- early fraud screening;
- reduced manual review;
- evidence-backed investigation.

## Demo rule

Never demo an untested live path if a known-good test case can demonstrate the feature more reliably.

The goal is to show a working system, not to gamble on model behavior.
