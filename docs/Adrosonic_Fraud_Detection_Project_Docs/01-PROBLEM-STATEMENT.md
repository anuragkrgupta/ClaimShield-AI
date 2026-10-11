# Adrosonic Problem Statement — Requirements

## Problem

**AI-Powered Synthetic Identity & Deepfake Claim Detection System**

Goal: detect AI-generated and manipulated content in digital insurance claims.

Insurance claims can contain diverse digital evidence across domains:
- accident or damage photographs (e.g., vehicle, property)
- medical reports and invoices
- repair estimates and receipts
- identity documents

*(Note: Vehicle accident damage is utilized as the primary demonstration scenario, but the core evidence analysis pipeline is designed to be insurance-domain agnostic).*

Generative AI and image manipulation tools create a fraud risk.

## Challenge

Build a working AI-powered fraud detection prototype that:
- analyzes uploaded images and documents;
- flags potentially synthetic or manipulated content;
- produces risk scoring;
- explains the reasons for the risk;
- provides an intuitive user experience.

The challenge emphasizes end-to-end solution design and product execution over building a sophisticated model that is poorly integrated.

## Required scope

### A. Image Manipulation Detection — MUST HAVE

The system should:
- use a pretrained or custom image manipulation/deepfake model;
- classify uploaded images as authentic or AI-generated/manipulated;
- provide confidence;
- flag images above a defined risk threshold;
- optionally highlight suspicious regions.

### B. Document Tampering Detection — MUST HAVE

Analyze uploaded PDF/image documents for:
- inconsistent fonts;
- altered values;
- metadata anomalies;
- OCR-extracted text inconsistencies;
- suspicious fields with reasons.

### C. Risk Scoring — MUST HAVE

Produce:
- image authenticity score;
- document authenticity score;
- overall fraud likelihood;
- interpretable reasons.

### D. Demo Interface — MUST HAVE

Provide a web UI where a user can:
- upload files;
- see results;
- see fraud score;
- see flagged indicators;
- read a short plain-English explanation.

Accepted UI approaches include Streamlit, Gradio, or basic React/Flask.

### E. Identity Comparison — BONUS

Compare:
- ID-document face
- selfie image

Use the comparison to detect mismatch or morphing.

## Challenge constraints

- 24-hour challenge
- team size: 2–4
- pretrained models allowed
- limited authentic/fraud data expected
- synthetic/tampered data may be generated
- system should handle data-quality variation such as low resolution, noise, compression artifacts, and incomplete inputs.

## Evaluation

| Criterion | Weight |
|---|---:|
| Detection accuracy | 25% |
| Risk scoring & explainability | 25% |
| UI / demo quality | 20% |
| Code quality & architecture | 15% |
| Innovation / bonus features | 15% |

## Demo requirements

The final demo should show:
1. image upload and detection confidence;
2. document upload and tampering flags/reasons;
3. composite risk score and explanation;
4. architecture and key decisions;
5. identity mismatch detection if implemented.

## Important interpretation

The target is not merely a classifier.

The product must demonstrate:

```text
Evidence
  -> Detection
  -> Reasoning
  -> Risk
  -> Explainable decision
  -> Human investigation
```

Source: Adrosonic Build problem statement, pages 2–5.
