# VerifAI vs Adrosonic — Gap Analysis

## Baseline

Reference repository: `Anupkrmi/SIH-2026-26188-VerifAI` (stored in `VerifAI_Ref/` as a read-only reference).

Initial alignment before modification: approximately **7/10**.

---

## Comparison & Current Implementation Status

| Requirement | VerifAI Reference | ClaimShield AI Current Status | Gap Status |
|---|---|---|---|
| AI-generated image detection | None | Implemented (UnivFD with CLIP ViT-L/14 backbone) | **Closed (Implemented)**; discrimination on natural images under empirical testing |
| Image-model confidence | Partial / implicit | Implemented (explicit synthetic probability & confidence in `Signal`) | **Closed (Implemented)** |
| Image authenticity score | None | Implemented (`calculate_image_authenticity` in `core/risk.py`) | **Closed (Implemented)** |
| Image forensics | ELA, noise, recapture | Phase 3 evaluated: ELA and noise **rejected**; Recapture **candidate** | **Resolved / Streamlined** |
| Document tampering | Passport-centric | Planned generic document pipeline | **Open (Phase 5)** |
| OCR text extraction | Present | Planned for generic insurance receipts/bills | **Open (Phase 5)** |
| Document authenticity score | Embedded in passport risk | Planned as standalone score layer | **Open (Phase 6)** |
| Claim consistency (Date / Amount) | Domain-specific checks | Planned deterministic P0 checks | **Open (Phase 4)** |
| Overall fraud likelihood | Tiered rules | Planned multi-tier fusion | **Open (Phase 6)** |
| Explainability | Present | Implemented `Signal` pattern; expanding to full claim | **Partially Closed** |
| Claim submission UI | Travel document upload | Single-image active; multi-evidence claim workflow planned | **Partially Closed** |
| Face comparison | Present | Retained as optional P1/Bonus | **Deferred (Bonus)** |

---

## Reusable Reference Strengths & Forensic Decisions

### 1. Evidence Fusion & Explainability
* The reference pattern of representing each check as an explicit signal with severity, numeric score, and plain-English message was preserved in ClaimShield AI (`Signal` in `core/types.py`).

### 2. Forensics Evaluation (Phase 3 Findings)
* **Error Level Analysis (ELA):** Evaluated and **rejected** for ClaimShield AI. ELA produces widespread false positives on legitimate camera images saved with variable compression.
* **Noise Analysis:** Evaluated and **rejected**. VerifAI's noise analysis is tuned for high-contrast ID documents and produces noisy, misleading flags on natural camera photos.
* **Recapture Detection:** Retained as a **candidate** supporting layer (detecting screen display Moiré patterns and JPEG grid blockiness) to support the primary AI detector.

---

## Gap Resolution Summary

### Gap 1 — Dedicated AI Image Model [CLOSED]
UniversalFakeDetect (UnivFD) was integrated in `core/image/detector.py` with CLIP ViT-L/14 backbone and custom FC head weights.
* *Note on Model Discrimination:* Initial empirical validation in Phase 2 demonstrated that UnivFD produced similar authenticity scores on real (~69.16%) versus AI-generated car-damage (~72.53%) photos. The model provides an advisory synthetic likelihood, not definitive proof of fraud.

### Gap 2 — Insurance Claim Abstraction [OPEN — Phase 4]
Transition from single-file inspection to an insurance claim entity:
```text
Claim (Claim ID, Claimant, Incident Date, Claimed Amount)
  ├── Images (Damage photos, scene photos)
  └── Documents (Invoices, repair estimates, medical bills)
```

### Gap 3 — Generic Document Tampering [OPEN — Phase 5]
Screening general insurance documents for OCR discrepancies, altered values, and metadata anomalies without travel-document constraints.

### Gap 4 — Multi-Tier Scoring [OPEN — Phase 6]
Expanding beyond the currently implemented Image Authenticity Score to:
* Document Authenticity Score (0–100)
* Claim Consistency Score (0–100)
* Overall Fraud Likelihood (0–100)

### Gap 5 — Cross-Evidence Consistency [OPEN — Phase 4]
Deterministic checks:
* Incident date vs. document/metadata dates (P0).
* Claimed amount vs. invoice/estimate totals (P0).
* Claimant name matching (P1).
