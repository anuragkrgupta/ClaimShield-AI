# Feature Requirements

## P0 — Must Work (Core MVP)

### F1. Claim upload [Planned]
- Create a claim container.
- Upload one or more evidence files (images/documents).
- Associate files with the claim record.

### F2. Image AI detection [Implemented]
- Input: JPG/PNG and common image formats.
- Implementation: UniversalFakeDetect (UnivFD) with CLIP ViT-L/14 backbone and custom head.
- Output:
  - Synthetic probability / AI-generation likelihood (`confidence`).
  - Image Authenticity Score (0–100, where higher is more authentic).
  - Severity level (`HIGH` for fake, `LOW` for authentic).
  - Plain-English explanation signal.

### F3. Supporting image forensics [Planned Candidate / Supporting]
- Supporting indicators to complement the primary AI detector:
  - Recapture detection (Moiré pattern and JPEG-blockiness) — *Proposed candidate awaiting implementation*.
  - Image format and EXIF metadata checks — *Planned*.
- *Decision Note:* Error Level Analysis (ELA) and reference noise analysis were evaluated and **excluded** from P0 requirements due to reliability issues on natural scene images.

### F4. Document OCR [Planned]
- Extract text from uploaded PDF/image documents.
- Identify relevant financial and timeline fields (dates, amounts, provider names).
- Retain extracted text for auditability and explanation.

### F5. Document tampering [Planned]
- Check metadata anomalies (creation date vs modification date).
- Visual and layout inconsistencies / altered text values.
- Emit structured signals with explainable reasons.

### F6. Multi-tier risk scoring [Partially Implemented]
- Current: `calculate_image_authenticity()` active in `core/risk.py`.
- Planned:
  - Document Authenticity Score (0–100).
  - Claim Consistency Score (0–100).
  - Overall Fraud Likelihood (0–100) combining all evidence layers.

### F7. Explainability [Implemented Pattern, Expanding]
- Every non-trivial flag emits a `Signal` with:
  - `name`: Identifier of the check.
  - `severity`: Severity level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `score`: Numeric impact on authenticity.
  - `confidence`: Confidence or probability estimate.
  - `message`: Plain-English explanation.

### F8. Web UI [Single-Image Implemented, Multi-file Planned]
- Current: Single-image upload, analysis trigger, score display, and signal explanations in `app.py`.
- Planned: Complete claim workflow with multi-evidence submission and composite dashboard.

### F9. Basic claim consistency [Planned — P0]
- **Date consistency:** Incident date vs. document/metadata dates.
- **Amount consistency:** Claimed amount vs. extracted invoice/estimate totals.

---

## P1 — High-Value (Next Priority)

### F10. Advanced claim consistency
- Claimant name fuzzy matching across multiple documents.
- Cross-document timeline alignment.
- Advanced claim metadata relationships.

### F11. Identity comparison (Bonus)
- Compare facial biometric features between uploaded ID document and selfie.
- Flag face mismatch or morphing indicators.

---

## P2 — Polish & Enhancements

- Suspicious-region heatmap visualizations.
- Synthetic attack generator for test augmentation.
- Support for specialized domain forms (e.g., medical coding, repair line items).
- Downloadable PDF investigation report.

---

## Acceptance Criteria

### Image
Given an uploaded image:
- The detector executes gracefully (without crashing on valid, corrupt, or empty inputs).
- A synthetic probability and Image Authenticity Score are produced.
- UnivFD is presented as an advisory model signal; an AI-generation likelihood is not treated as definitive legal proof of fraud.

### Document
Given a tampered document:
- Discrepant fields or metadata anomalies generate visible warning signals.
- Plain-English reasons explain why the document is flagged.

### Risk
Given multiple evidence signals:
- Scores are deterministic and reproducible.
- Contributing signals clearly map to the final risk assessment.
- The system highlights suspicious findings without presenting false certainty.

### UI
An evaluator can:
1. Upload claim files.
2. Run analysis.
3. Understand the fraud assessment and contributing evidence within seconds.

---

## Priority Rule

If time becomes limited:

```text
P0 > P1 > P2
```

Never sacrifice a working P0 feature to add a P2 enhancement. Basic date and amount consistency checks belong in P0.
