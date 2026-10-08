# Final Readiness Checklist

## Problem alignment

- [ ] Image manipulation detection implemented
- [ ] AI-generated image detection implemented
- [ ] Confidence shown
- [ ] Document tampering detection implemented
- [ ] OCR implemented
- [ ] Metadata checks implemented
- [ ] Suspicious fields shown
- [ ] Reasons shown
- [ ] Image authenticity score shown
- [ ] Document authenticity score shown
- [ ] Overall fraud likelihood shown
- [ ] Risk explanation shown
- [ ] Working upload UI
- [ ] Identity comparison implemented if time allows

## Image pipeline

- [ ] Preprocessing works
- [ ] AI/deepfake model loads reliably
- [ ] Genuine sample tested
- [ ] AI-generated sample tested
- [ ] Manipulated sample tested
- [ ] Low-resolution sample tested
- [ ] Compressed sample tested
- [ ] Detector failure handled
- [ ] Confidence displayed
- [ ] Forensic indicators displayed

## Document pipeline

- [ ] PDF upload works
- [ ] Image-document upload works
- [ ] OCR works
- [ ] Metadata extraction works
- [ ] Tampering checks work
- [ ] Field extraction works
- [ ] Suspicious fields have reasons
- [ ] OCR failure handled

## Claim consistency

- [ ] Name consistency
- [ ] Date consistency
- [ ] Amount consistency
- [ ] Claim ID consistency
- [ ] Metadata/timeline check
- [ ] Cross-evidence result visible

## Risk engine

- [ ] Image score
- [ ] Document score
- [ ] Claim consistency score
- [ ] Overall score
- [ ] Thresholds centralized
- [ ] Reasons match signals
- [ ] Missing evidence handled
- [ ] Detector failure handled
- [ ] No unexplained hard-coded score logic

## UI

- [ ] Upload is obvious
- [ ] Analyze button works
- [ ] Progress/status is understandable
- [ ] Overall risk is visible immediately
- [ ] Scores are readable
- [ ] Reasons are readable
- [ ] Evidence details accessible
- [ ] No debug output visible
- [ ] No broken controls

## Reliability

- [ ] Fresh environment tested
- [ ] Clean browser tested
- [ ] Multiple files tested
- [ ] Invalid file tested
- [ ] Corrupt file tested
- [ ] Large file tested
- [ ] Model load failure tested
- [ ] OCR failure tested

## Code

- [ ] No duplicate functions
- [ ] No dead imports
- [ ] No unnecessary abstractions
- [ ] No unused services
- [ ] Configuration centralized
- [ ] Errors handled
- [ ] Important logic documented
- [ ] Existing tests still pass

## Demo

- [ ] Clean claim demo ready
- [ ] Fraudulent image demo ready
- [ ] Tampered document demo ready
- [ ] Composite-risk demo ready
- [ ] Identity mismatch demo ready if implemented
- [ ] Architecture diagram ready
- [ ] 10-minute story rehearsed
- [ ] Backup demo files ready

## Final quality gate

The system should answer three questions clearly:

### 1. Is the image suspicious?
Show:
- result;
- confidence;
- evidence.

### 2. Is the document suspicious?
Show:
- tampering indicators;
- fields;
- reasons.

### 3. Why is this claim high/medium/low risk?
Show:
- evidence;
- scores;
- explanation.

If these three answers are clear, the core product is ready.
