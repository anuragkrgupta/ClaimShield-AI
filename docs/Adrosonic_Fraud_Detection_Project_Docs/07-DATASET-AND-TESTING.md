# Dataset, Synthetic Data and Testing Plan

## Challenge data reality

The problem statement anticipates:
- limited authentic images;
- limited real-world fraud data;
- need for synthetic/tampered examples;
- variations in resolution, noise and compression.

## Dataset categories

### Authentic

```text
images/
documents/
identity/
invoices/
reports/
```

### Manipulated

Create representative attack classes:

```text
AI_GENERATED
OBJECT_INSERTION
OBJECT_REMOVAL
COPY_PASTE
LOCAL_EDIT
SCREEN_RECAPTURE
COMPRESSION
DOCUMENT_VALUE_EDIT
DOCUMENT_TEXT_EDIT
METADATA_CHANGE
```

## Do not overfit to one attack

The challenge expects robustness against unseen/novel patterns.

Therefore, don't make the detector depend on one visible artifact.

Use multiple evidence types.

## Synthetic test matrix

| Case | Image | Document | Consistency | Expected |
|---|---|---|---|---|
| Clean | genuine | genuine | consistent | LOW |
| AI image | synthetic | genuine | consistent | HIGH |
| Edited image | manipulated | genuine | consistent | MEDIUM/HIGH |
| Tampered doc | genuine | tampered | inconsistent | HIGH |
| Date mismatch | genuine | genuine | inconsistent | MEDIUM/HIGH |
| Amount mismatch | genuine | genuine | inconsistent | MEDIUM |
| Identity mismatch | genuine | genuine | mismatch | HIGH |
| Multiple attacks | manipulated | tampered | inconsistent | HIGH/CRITICAL |

These are target test scenarios, not guaranteed model outcomes.

## Image testing

For every image test:
- original resolution;
- resized;
- JPEG compressed;
- noisy;
- low resolution.

The detector should not fail simply because the input is imperfect.

## Document testing

Test:
- clean PDF;
- scanned document;
- image document;
- edited value;
- edited date;
- metadata changed;
- low-quality scan.

## Failure handling

If a detector cannot process an input:
- do not crash the entire claim;
- create an "analysis unavailable" signal;
- continue other checks;
- make the limitation visible.

## Regression suite

Every fixed bug should become a test.

Especially test:
- score calculation;
- missing files;
- model loading;
- malformed documents;
- OCR failures;
- unsupported formats;
- UI state;
- multiple evidence items.

## Accuracy reporting

For the final demo, report simple metrics where available:
- accuracy;
- precision;
- recall;
- F1;
- confusion matrix.

Do not claim production accuracy from a tiny synthetic demo set.
