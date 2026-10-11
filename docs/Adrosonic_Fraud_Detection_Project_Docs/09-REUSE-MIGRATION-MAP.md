# VerifAI Reuse and Migration Map

## Reference Repository

Reference location: `VerifAI_Ref/` (`Anupkrmi/SIH-2026-26188-VerifAI`)

> **Architectural Precondition:** ClaimShield AI is a **standalone project**, not an in-place mutation or fork of VerifAI. The `VerifAI_Ref/` directory is an external, read-only reference for selective ideas, design patterns, and standalone algorithms. Do not attempt in-place edits or direct module imports from `VerifAI_Ref/`.

---

## Selective Reuse Evaluation

### 1. Risk Architecture & Signal Pattern
* **Reference concept:** Tiered evidence, discrete `Signal` objects, severity tiers, and centralized policy rules.
* **ClaimShield action:** Reused and adapted in `core/types.py` (`Signal` dataclass) and `core/risk.py`. Expand in later phases to multi-tier score fusion (Image Authenticity, Document Authenticity, Claim Consistency, Overall Fraud Likelihood).

### 2. Forensics Evaluation (Phase 3 Findings)
* **Error Level Analysis (ELA):** **REJECTED.** Evaluated during Phase 3 and excluded from the generic evidence pipeline due to severe false-positive rates on natural-scene and web-compressed images.
* **Noise Analysis:** **REJECTED for generic images.** VerifAI's noise variance detector was tuned for clean, high-contrast travel documents and produces misleading flags on natural camera scenes.
* **Recapture Detection:** **CANDIDATE ONLY.** A lightweight reimplementation of Moiré pattern and JPEG-blockiness analysis was proposed as a supporting forensic layer. Awaiting implementation and empirical validation.
* **Heatmaps & visual masks:** **DEPRIORITIZED.** Deemed optional P2 polish; not required for the core MVP.

### 3. Identity Verification (Face Matching)
* **Reference concept:** Face detection and comparison between ID document and selfie.
* **ClaimShield action:** Retained strictly as an optional **P1/Bonus** capability. Do not introduce before core claim and document evidence pipelines are functional.

### 4. UI Patterns
* **Reference concept:** Streamlit component layouts, clear score banners, and evidence lists.
* **ClaimShield action:** Adopt layout philosophy in `app.py`. Adapt terminology completely to insurance claims (Claimant, Evidence, Damage Photos, Invoices, Consistency).

### 5. Document Processing
* **Reference concept:** OCR extraction and basic layout/field consistency checks.
* **ClaimShield action:** Reference implementation for generic document screening (receipts, medical bills, repair estimates) in a future planned `core/document/` module.

---

## What NOT to Port (Excluded Assumptions)

The following reference components are passport-specific and are **completely excluded** from ClaimShield AI:
* TD3 / MRZ (Machine Readable Zone) parsing and check-digit algorithms.
* Country-specific issuer registry and authority signatures.
* ICAO Doc 9303 cryptographic checks.
* Passport-only synthetic tamper generators.

---

## Module Status in ClaimShield AI

| Module | Status | Role in ClaimShield AI |
|---|---|---|
| `core/types.py` | **Implemented** | Core `Signal` dataclass |
| `core/risk.py` | **Implemented (Initial)** | `calculate_image_authenticity()` active; multi-tier fusion planned |
| `core/image/detector.py` | **Implemented** | UnivFD AI-generation detection with CLIP backbone |
| `core/image/forensics.py` | **Proposed Candidate** | Recapture detection (Moiré / Blockiness) awaiting implementation |
| `core/claim/` | **Planned (P0)** | Claim container & basic date/amount consistency checks |
| `core/document/` | **Planned (P0)** | Generic OCR & document tampering detection |
| `core/identity/` | **Planned (Bonus)** | Face comparison between ID and selfie |

---

## Architectural Rule

Do not maintain competing or parallel architectures:
* Build the minimal, clean ClaimShield AI pipeline.
* Import or reimplement only the exact algorithms needed to satisfy a verified requirement.
* Keep ClaimShield decoupled from VerifAI's internal dependencies.
