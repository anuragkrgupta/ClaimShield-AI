# VerifAI Reuse and Migration Map

## Reference repository

`Anupkrmi/SIH-2026-26188-VerifAI`

## KEEP / strongly reuse

### Risk architecture
Existing:
- evidence/signals;
- severity;
- tiered decision logic;
- centralized policy.

Action:
- adapt categories to insurance evidence.

### Forensics
Reuse:
- ELA;
- noise;
- recapture;
- image-region analysis;
- heatmap/visualization where useful.

### Face
Reuse:
- face detection/comparison infrastructure.

Use as bonus unless required earlier.

### UI
Reuse:
- Streamlit structure;
- components;
- result rendering concepts.

### Tests
Reuse:
- test organization;
- signal-level tests;
- end-to-end pipeline testing philosophy.

### Synthetic-data approach
Reuse the idea of generating known attack cases for validation.

## MODIFY

### `core/pipeline.py`

Change from:

```text
passport screening
```

to:

```text
claim evidence screening
```

The pipeline should dispatch based on evidence type.

### `core/risk.py`

Keep the evidence-fusion concept.

Add categories:
- image;
- document;
- claim consistency;
- identity.

### `core/realdoc/`

Generalize from passport/document-specific assumptions toward:
- claim forms;
- invoices;
- reports;
- identity documents.

### `ui/`

Change product terminology:
- passport/case → claim;
- document screening → claim analysis;
- issuer checks → evidence/claim checks.

## DEPRIORITIZE / eventually remove

- TD3/MRZ-only logic;
- passport-specific issuer registry;
- passport attack generator;
- passport-specific cryptographic workflow;
- passport-only synthetic cases.

Do not delete them before the replacement workflow works.

## NEW

### `core/image/detector.py`

Dedicated AI/deepfake model.

### `core/claim/`

Claim object and cross-evidence consistency.

### `core/document/`

Generic document abstraction.

## Migration principle

Do not duplicate two competing pipelines.

Bad:

```text
old passport pipeline
+
new insurance pipeline
+
two different risk engines
```

Better:

```text
common evidence infrastructure
        +
domain-specific adapters
        +
one risk engine
```

## End state

```text
               Claim
                 |
        +--------+--------+
        |                 |
      Image            Document
        |                 |
   AI + forensics     OCR + tamper
        |                 |
        +--------+--------+
                 |
          Claim consistency
                 |
          Identity (bonus)
                 |
             Risk Engine
                 |
          Explainable Result
```
