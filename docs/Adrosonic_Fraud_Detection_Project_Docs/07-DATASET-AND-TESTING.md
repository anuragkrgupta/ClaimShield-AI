# Dataset, Synthetic Data and Testing Plan

## Challenge Data Reality

The problem statement anticipates:
* Limited access to real-world insurance fraud data.
* Need to synthesize and test realistic attack patterns.
* Variations in real-world image quality (compression, resolution, sensor noise).

---

## Testing Tiers and Current Status

Do not conflate passing unit tests with model accuracy:

### 1. Automated Unit Tests [Implemented & Passing]
* **Location:** `tests/test_pipeline.py` (6 tests passing).
* **Scope:** Unit test suite using `unittest.mock` to isolate pipeline logic, verify signal creation, test empty/invalid byte handling, and validate `calculate_image_authenticity()`.
* **Execution Command:**
  ```bash
  python -m pytest tests/test_pipeline.py
  ```
  *(Always specify the test path to avoid running reference scripts in `VerifAI_Ref/`)*.
* **Important Note:** These tests pass using mocked predictions; they do **not** evaluate live model accuracy.

### 2. Live Empirical Model Validation [Implemented Tool]
* **Location:** `validate_phase2.py`.
* **Scope:** Measures real model initialization time, memory footprint, and CPU inference latency across real, corrupt, and synthetic image inputs.
* **Execution Command:**
  ```bash
  python validate_phase2.py [path/to/ai_image.jpg]
  ```

### 3. Historical Phase 2 Validation Findings
During Phase 2 integration testing:
* **Real Photograph (Wikipedia car photo):** Scored approximately **69.16%** image authenticity.
* **AI-Generated Image (Car damage):** Scored approximately **72.53%** image authenticity.
* **Finding:** The model did not meaningfully separate this pair of test images.
* **Guidance:** UnivFD output is an advisory indicator. Documentation and UI must not claim that the model reliably detects every synthetic image, or that passing unit tests prove detection accuracy.

---

## Target Scenario Matrix (Planned Validation)

| Scenario | Image Evidence | Document Evidence | Consistency Check | Expected Composite Risk | Current Status |
|---|---|---|---|---|---|
| Clean Claim | Genuine photo | Genuine invoice/receipt | Dates & amounts match | `LOW` | Planned |
| AI Damage Image | Synthetic image | Genuine document | Consistent | `MEDIUM / HIGH` | Partially tested (UnivFD active) |
| Tampered Document | Genuine photo | Altered amount/date | Inconsistent | `HIGH` | Planned (Phase 4/5) |
| Date Mismatch | Genuine photo | Genuine document | Incident date != Invoice date | `MEDIUM / HIGH` | Planned (Phase 4) |
| Amount Discrepancy | Genuine photo | Genuine document | Claimed > Invoice total | `MEDIUM` | Planned (Phase 4) |
| Identity Mismatch | Genuine photo | ID != Selfie face | Biometric mismatch | `HIGH` | Planned (Bonus) |
| Multi-Attack | Synthetic image | Tampered document | Inconsistent | `HIGH / CRITICAL` | Planned |

*Note: These are target scenario specifications for future end-to-end evaluation, not guaranteed model benchmark outcomes.*

---

## Robustness & Failure Handling Requirements

1. **Corrupt & Empty Inputs:** The image detector must handle malformed, truncated, or zero-byte files gracefully (`(None, False)`) without crashing the application.
2. **Missing Dependencies/Weights:** If `fc_weights.pth` is missing or transformers cannot be loaded, the app must display an "Analysis Unavailable" status rather than crashing.
3. **Resolution & Compression:** Evaluate inputs across native resolution, downscaled images, and compressed JPEGs to understand real-world degradation.

---

## Accuracy Reporting Principles

For final release and hackathon presentation:
* Report empirical metrics (Accuracy, Precision, Recall) only on explicitly verified, representative datasets.
* Do not claim production-grade accuracy from small demo samples.
* Clearly differentiate between unit test pass rates and empirical classification accuracy.
