# Feature Requirements

## P0 — Must work

### F1. Claim upload
- Create a claim.
- Upload one or more images/documents.
- Associate files with the claim.

### F2. Image AI detection
Input:
- JPG/PNG and common image formats.

Output:
- authentic/manipulated/AI-generated classification;
- confidence;
- authenticity score;
- explanation.

### F3. Image forensics
Run reusable forensic checks:
- ELA;
- noise;
- recapture;
- metadata if available.

### F4. Document OCR
- extract text;
- identify relevant fields;
- retain OCR result for explanation.

### F5. Document tampering
Check:
- suspicious visual regions;
- metadata;
- inconsistent fields;
- suspicious values;
- OCR-derived inconsistencies.

### F6. Risk scoring
Produce:
- image authenticity;
- document authenticity;
- overall fraud likelihood.

### F7. Explainability
Every non-trivial flag should include:
- what was checked;
- result;
- reason;
- supporting evidence.

### F8. UI
Must support:
- upload;
- analyze;
- results;
- score;
- reasons.

### F9. Basic claim consistency
Check:
- date consistency;
- amount consistency.

## P1 — High-value

### F10. Advanced claim consistency
Check:
- name;
- claim ID;
- document consistency;
- image timeline metadata.

### F11. Identity comparison
Compare:
- ID face;
- selfie/claimant face.

## P2 — Bonus

- suspicious-region heatmap;
- synthetic attack generator;
- richer document types;
- vehicle-damage-specific model;
- medical-report field validation;
- downloadable report.

## Acceptance criteria

### Image
Given a known manipulated sample:
- detector produces a suspicious result;
- confidence is shown;
- at least one reason is shown.

### Document
Given a tampered sample:
- suspicious indicator is shown;
- reason is shown;
- OCR/field result is visible where applicable.

### Risk
Given multiple signals:
- scores are reproducible;
- explanation matches contributing evidence;
- overall result is not a black box.

### UI
A new evaluator should be able to:
1. upload evidence;
2. run analysis;
3. understand the result without reading source code.

## Priority rule

If time becomes limited:

```text
P0 > P1 > P2
```

Never sacrifice a working P0 feature to add a P2 feature.
