# Risk Engine and Explainability

## Objective

Turn heterogeneous evidence into a clear, defensible fraud-likelihood result.

## Core principle

Do not treat every signal as equally reliable.

Example:

```text
Dedicated AI detector
        = primary evidence

ELA
Noise
Recapture
Metadata
        = supporting evidence

Cross-document mismatch
        = deterministic evidence
```

## Suggested score layers

### 1. Image Authenticity Score

Range:

```text
0 = highly suspicious
100 = highly authentic
```

Inputs:
- AI/deepfake model;
- ELA;
- noise;
- recapture;
- metadata.

### 2. Document Authenticity Score

Inputs:
- OCR consistency;
- metadata;
- tampering signals;
- field consistency;
- visual evidence.

### 3. Claim Consistency Score

Inputs:
- name;
- dates;
- amounts;
- IDs;
- document relationships;
- image timeline.

### 4. Overall Fraud Likelihood

Range:

```text
0 = low fraud likelihood
100 = high fraud likelihood
```

## Example

```text
Image authenticity       22
Document authenticity    64
Claim consistency        35
Identity match           96
```

The identity score should not automatically cancel strong fraud evidence.

## Explainability record

Each signal should preserve:

```python
{
    "check": "...",
    "category": "...",
    "severity": "...",
    "score": ...,
    "confidence": ...,
    "message": "...",
    "detail": {...}
}
```

## Example explanation

```text
HIGH FRAUD LIKELIHOOD — 74%

Primary indicators:
- AI-generation probability: 91%
- Document alteration indicator detected
- Claim amount differs from supporting invoice

Supporting indicators:
- ELA anomaly
- Metadata inconsistency

Identity:
- Face matches submitted ID
```

## Important safety rule

The score is a fraud-risk signal, not a legal determination.

Use language such as:
- "potentially manipulated";
- "suspicious";
- "high fraud likelihood";
- "secondary review recommended."

## Avoid false confidence

Do not display:

```text
100% FRAUD
```

unless the system has an explicitly justified deterministic rule and the product requirements truly support such a conclusion.

For model-based evidence, confidence should be described as model confidence/probability, not certainty.

## Configuration

Risk weights and thresholds should live in one configuration/policy location.

Avoid:

```python
if score > 63:
```

scattered across many files.

Prefer a centralized policy.

## Testing the risk engine

Test:
- no signals;
- one weak signal;
- one strong model signal;
- multiple supporting signals;
- conflicting signals;
- missing detector output;
- detector failure;
- missing metadata.

The same input evidence should produce the same result.
