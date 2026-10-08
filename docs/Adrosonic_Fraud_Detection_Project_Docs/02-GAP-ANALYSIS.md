# VerifAI vs Adrosonic — Gap Analysis

## Baseline

Reference:
`Anupkrmi/SIH-2026-26188-VerifAI`

Estimated similarity to the challenge before modification: **7/10**.

This is an engineering judgment, not a benchmark.

## Comparison

| Requirement | VerifAI | Gap |
|---|---|---|
| Image manipulation detection | ELA, noise, recapture and forensic signals | Needs dedicated AI/deepfake classifier |
| AI-generated image detection | No dedicated detector confirmed | **Major gap** |
| Confidence score | Partial through signals/risk | Need explicit image-model confidence |
| Document tampering | Strong | Generalize beyond passport workflow |
| OCR | Present | Reuse |
| Suspicious fields/reasons | Present | Generalize |
| Image authenticity score | Partial | Add explicit score |
| Document authenticity score | Present through risk architecture | Generalize |
| Overall fraud risk | Strong | Adapt to claim evidence |
| Explainability | Strong | Reuse |
| Upload/results UI | Streamlit | Reuse/adapt |
| Face comparison | Present | Reuse as bonus |
| Insurance claim workflow | Not core | **Major gap** |
| Vehicle damage analysis | Not core | Optional/phase 2 |
| Medical report analysis | Not core | Generic document workflow first |
| Cross-claim/evidence consistency | Limited / domain-specific | Add |
| Synthetic attack testing | Strong for document domain | Adapt |

## Existing strengths

### 1. Evidence fusion

VerifAI has a tiered risk philosophy:
- cryptographic evidence can be decisive;
- deterministic rule/issuer failures can be decisive;
- forensic/biometric signals are advisory.

For the insurance version, preserve the principle:

> strong evidence should have stronger decision authority than weak forensic hints.

### 2. Forensics

Useful reusable components:
- ELA
- noise analysis
- recapture detection
- image-region analysis
- heatmap/visual evidence where available

### 3. Document pipeline

Useful concepts:
- OCR
- field extraction
- cross-field consistency
- metadata
- document/image forensics
- structured signals

### 4. Explainability

Every flag should have:
- check name;
- result;
- severity;
- reason;
- supporting value/detail where possible.

## Major gaps

### Gap 1 — Dedicated AI/deepfake model

Current forensics are not enough for the challenge's model requirement.

Solution:
- integrate one pretrained image authenticity/deepfake detector;
- hide model-specific code behind a simple detector interface.

### Gap 2 — Insurance claim abstraction

Replace passport-centric workflow with:

```text
Claim
  -> Evidence
     -> Images
     -> Documents
     -> Identity evidence
```

### Gap 3 — Generic document tampering

Move from passport/MRZ-specific logic toward:
- claim forms
- invoices
- medical reports
- repair estimates
- identity documents.

Passport-specific modules can remain available temporarily but should not drive the new architecture.

### Gap 4 — Explicit score categories

Add:
- Image Authenticity Score
- Document Authenticity Score
- Claim Consistency Score
- Overall Fraud Likelihood

### Gap 5 — Cross-evidence consistency

Add checks such as:
- claimant name mismatch;
- date mismatch;
- claim amount vs invoice amount;
- document metadata vs claimed incident date;
- identity mismatch.

## Target

After closing these gaps:

```text
Existing VerifAI
      +
AI image detector
      +
Insurance claim layer
      +
Generic document analysis
      +
Cross-evidence consistency
      +
Explicit score presentation
      =
Adrosonic-aligned prototype
```
