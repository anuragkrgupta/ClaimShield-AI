# Implementation Roadmap

This roadmap governs the development sequence for ClaimShield AI. Phases must not advance automatically without verified completion criteria.

---

## Phase 1 — Minimal Scaffold [COMPLETED]

### Goal
Establish the standalone project scaffold and core data structures.

### Deliverables
* Minimal standalone repository structure created.
* Standard `Signal` dataclass implemented in `core/types.py`.
* Initial `calculate_image_authenticity()` score function in `core/risk.py`.
* Initial Streamlit application shell in `app.py`.
* Baseline unit tests with mocks in `tests/test_pipeline.py` (6 tests passing).

---

## Phase 2 — UnivFD Model Integration [COMPLETED]

### Goal
Replace early mock detection with a real, pretrained AI/deepfake image detector.

### Deliverables
* UniversalFakeDetect (UnivFD) integrated in `core/image/detector.py`:
  * Pretrained CLIP ViT-L/14 backbone loaded via HuggingFace Transformers.
  * Trained linear classification head loaded from `fc_weights.pth` (768 -> 1).
  * Graceful fallback when weights or libraries are missing.
* Detector exposed via `analyze_image_univfd(image_bytes: bytes) -> Tuple[Optional[Signal], bool]`.
* Streamlit UI updated to run single-image analysis and render Image Authenticity Score and reasons.
* Empirical validation script implemented in `validate_phase2.py`.

### Technical Findings & Limitations
* **Validation Outcome:** Validation on sample images yielded approximately 69.16% authenticity for a real car photo and 72.53% for an AI-generated damaged car image.
* **Discrimination:** The initial model did not cleanly differentiate the two test samples on CPU inference.
* **Operational Rule:** UnivFD's output is an advisory signal of synthetic likelihood, **not** definitive proof of authenticity or fraud.

---

## Phase 3 — Forensic Evaluation [COMPLETED EVALUATION]

### Goal
Evaluate reference forensic techniques from VerifAI for use in ClaimShield AI's generic natural-image pipeline.

### Findings
* **Error Level Analysis (ELA):** **REJECTED.** Excluded from the generic image pipeline due to high false-alarm rates caused by camera ISP differences and web compression.
* **Noise Analysis:** **REJECTED for generic images.** VerifAI's noise analysis relies on document-specific assumptions that do not generalize to outdoor camera scenes.
* **Recapture Detection:** **CANDIDATE ONLY.** A lightweight check for Moiré patterns and JPEG-blockiness was proposed.
* **Status:** The forensic evaluation is complete. The candidate recapture detector has **not** been implemented in code.

### Decision Gate
* **Next Action:** The team may choose to validate and implement candidate recapture detection or proceed directly to Phase 4 (Claim Layer & Basic Consistency). Recapture detection is a supporting check and is **not a blocker** for building the claim layer.

---

## Phase 4 — Claim Layer & Basic Consistency [COMPLETED]

### Goal
Introduce the core claim entity and deterministic cross-evidence checks.

### Deliverables
1. Defined deterministic claim data structure in `core/claim/models.py`:
   * `Claim`: Metadata (Claim ID, Claimant Name, Incident Date, Claim Date, Claimed Amount, Claim Type) and evidence container.
   * `EvidenceItem`: Evidence items with extracted dates, amounts, and metadata.
2. Implemented basic **P0** deterministic consistency checks in `core/claim/consistency.py`:
   * **Date Consistency:** Formats validation, incident date vs claim filing date, and evidence date predating incident.
   * **Amount Consistency:** Formats/numeric validation, non-negativity, and claimed amount vs supporting evidence totals.
3. Emitted explainable `Signal` objects distinguishing malformed/invalid inputs from genuine factual contradictions.
4. Comprehensive unit test suite in `tests/test_claim_consistency.py` (11 passing tests).

---

## Phase 5 — Generic Document Analysis & Cross-Evidence Verification [IMPLEMENTED — P0]

### Goal
Screen uploaded claim documents (bills, repair estimates, medical reports) without passport-specific logic, inspect document authenticity and metadata tampering, and perform cross-evidence verification against images and claim details.

### Completed Capabilities
1. Generic text and metadata extraction from PDF (PyMuPDF) and images (PIL/PyTesseract) in `core/document/extractor.py`.
2. Extracted dates, monetary amounts, and document identifiers (invoice IDs, policy numbers).
3. Document tampering and metadata anomaly detection in `core/document/tampering.py` (consumer editing software detection, modification date discrepancies, synthetic repetition anomalies).
4. Cross-evidence relationship checks in `core/claim/cross_evidence.py`:
   * Deterministic identifier and claim ID consistency.
   * Cross-evidence date and amount data sufficiency.
   * Zero-shot image–document semantic relationship screening via CLIP ViT-L/14, categorizing relationships into `CONSISTENT`, `POTENTIAL_INCONSISTENCY`, and `INSUFFICIENT_INFORMATION`.
5. Graceful handling of empty, corrupt, and unreadable files.
6. Full test suite in `tests/test_document_analysis.py` (11 tests passing, 28 tests passing across full suite).


---

## Phase 6 — Multi-Tier Risk Fusion Engine [PLANNED — P0]

### Goal
Synthesize heterogeneous signals into an explainable composite risk assessment.

### Tasks
1. Implement the 4 score layers in `core/risk.py`:
   * **Image Authenticity Score (0–100)**: Active UnivFD + optional supporting recapture.
   * **Document Authenticity Score (0–100)**: OCR, metadata, visual tampering.
   * **Claim Consistency Score (0–100)**: Basic (and optional advanced) consistency checks.
   * **Overall Fraud Likelihood (0–100)**: Transparent, policy-based weighted fusion.
2. Centralize thresholds and scoring weights in `config.py`.
3. Generate plain-English explanation summaries tied directly to contributing signals.

---

## Phase 7 — End-to-End Streamlit Workflow [PLANNED — P0]

### Goal
Provide an intuitive evaluator workflow for submitting and reviewing an entire claim.

### Tasks
1. Expand `app.py` from single-image upload to complete claim submission:
   * Claim details input form.
   * Multi-file upload (damage photos, supporting documents).
2. Render overall fraud likelihood banner, tier scores, and itemized evidence findings.
3. Show plain-English explanations answering: *Why was this claim flagged?*

---

## Phase 8 — Testing, Robustness & Demo Hardening [PLANNED]

### Tasks
1. Expand automated tests:
   * Add unit tests for claim consistency logic.
   * Add tests for document extraction and risk fusion.
2. Robustness testing:
   * Missing files, corrupt files, unsupported formats.
   * Low-resolution images and OCR failure handling.
3. Rehearse 10-minute demo script with clean and suspicious claim scenarios.

---

## Phase 9 — Optional & Bonus Capabilities [PLANNED — P1/P2]

* **F10. Advanced Claim Consistency (P1):** Claimant name normalization, advanced document timeline checks.
* **F11. Identity Comparison (P1 Bonus):** Face matching between submitted ID document and selfie.
* **P2 Polish:** Downloadable PDF report, visual heatmaps.
