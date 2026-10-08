# Implementation Roadmap

## Phase 0 — Baseline

### Goal
Run the reference repository unchanged.

Tasks:
- clone repository;
- install dependencies;
- run Streamlit;
- test an existing sample;
- record known working state.

Do not modify architecture yet.

---

## Phase 1 — Dependency mapping

Identify:

```text
UI
 ↓
actions
 ↓
pipeline
 ↓
detectors
 ↓
risk
```

Mark each module:
- KEEP
- MODIFY
- DEPRECATE

Do not delete anything yet.

---

## Phase 2 — Claim layer

Create:
- claim object;
- evidence list;
- image/document classification;
- upload flow.

Expected result:

```text
Claim
  ├── image_1
  ├── image_2
  ├── claim_form.pdf
  └── invoice.pdf
```

---

## Phase 3 — AI image detector

Add:

```text
core/image/detector.py
```

Responsibilities:
1. preprocess;
2. load model;
3. infer;
4. normalize output;
5. return confidence;
6. return standardized evidence.

Do not let model-specific tensors or preprocessing leak into the risk engine.

---

## Phase 4 — Forensic fusion

Connect:
- AI detector;
- ELA;
- noise;
- recapture;
- metadata.

Primary evidence:
- model output.

Supporting evidence:
- forensic signals.

---

## Phase 5 — Generic documents

Retain reusable OCR/forensics infrastructure.

Generalize fields for:
- claim form;
- invoice;
- medical report;
- repair estimate;
- identity document.

Don't build every document type in the first pass.

---

## Phase 6 — Cross-evidence consistency

Start with deterministic high-value checks:

```text
Name ↔ Name
Date ↔ Date
Amount ↔ Amount
Claim ID ↔ Claim ID
Document date ↔ image metadata
```

Each check should create an explainable signal.

---

## Phase 7 — Risk engine

Create three visible layers:

```text
IMAGE AUTHENTICITY
DOCUMENT AUTHENTICITY
CLAIM CONSISTENCY
```

Then calculate:

```text
OVERALL FRAUD LIKELIHOOD
```

The exact formula should be documented and configurable.

Do not hard-code unexplained numbers throughout the code.

---

## Phase 8 — UI

Recommended pages:

### 1. New Claim
Upload evidence.

### 2. Analysis
Progress/status.

### 3. Results
Overall risk.

### 4. Evidence
Detailed image/document findings.

### 5. Explanation
Why the case was flagged.

---

## Phase 9 — Testing

Create known cases:

1. clean image + clean document;
2. AI-generated image;
3. manipulated image;
4. tampered document;
5. inconsistent dates;
6. inconsistent amounts;
7. identity mismatch;
8. multiple simultaneous indicators.

---

## Phase 10 — Demo hardening

Test:
- fresh browser;
- clean install;
- missing file;
- unsupported file;
- corrupt file;
- low-resolution image;
- large image;
- PDF;
- multiple uploads;
- model loading failure.

---

## Phase 11 — Cleanup

Only after functionality is stable:
- remove unused passport-specific modules;
- remove dead imports;
- remove duplicate functions;
- simplify unnecessarily complex paths;
- document final architecture.

Do not refactor working code merely for aesthetics during the critical implementation window.
