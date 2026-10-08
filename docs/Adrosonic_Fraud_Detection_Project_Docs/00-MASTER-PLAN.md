# AI-Powered Synthetic Identity & Deepfake Claim Detection System
## Master Project Blueprint

> Purpose: This document set preserves the complete plan for building
ClaimShield AI, a solution aligned with the Adrosonic Build problem
statement, using the existing `SIH-2026-26188-VerifAI` repository only
as a reference for selectively reusable components and approaches.

## 1. Source of truth

Primary problem statement:
- Adrosonic Build — *AI-Powered Synthetic Identity & Deepfake Claim Detection System*
- 24-hour hackathon
- Team size: 2–4
- Pre-trained models allowed
- Working UI required

The challenge asks for a working prototype that analyzes uploaded images/documents, flags potentially synthetic/manipulated content, produces risk scoring, and explains why a case was flagged.

Core requirements:
1. Image manipulation detection — MUST HAVE
2. Document tampering detection — MUST HAVE
3. Risk scoring and explainability — MUST HAVE
4. Demo upload/results UI — MUST HAVE
5. Identity comparison — BONUS

## 2. Starting point

Reference repository:

`https://github.com/Anupkrmi/SIH-2026-26188-VerifAI`

Current assessment:
- Approximate problem alignment before modification: **7/10**
- Strongest reusable areas: document screening, forensic analysis, evidence fusion, explainability, face comparison, Streamlit workflow.
- Largest gaps: dedicated AI/deepfake image detection, insurance-claim workflow, generic claim/evidence consistency.

## 3. Target

Target alignment after focused modification:
- **9–9.5/10** conceptually, assuming the new AI image detector works reliably on representative data and the final workflow is demonstrable.

This is a target, not a measured benchmark.

## 4. Target product

ClaimShield AI is an **insurance-agnostic digital evidence
authenticity and fraud detection system**.

Vehicle/accident insurance is only a demonstration scenario.

Possible claim evidence includes:

- accident or property-damage photographs
- medical documents and reports
- identity documents
- claim forms
- invoices and receipts
- repair estimates
- travel-related documents
- commercial/cargo evidence
- other digital claim evidence

The core system does not depend on the type of insurance.

The primary question is:

> Is the submitted digital evidence authentic, manipulated,
> AI-generated, or otherwise suspicious?

```text
Insurance Claim
      |
      +-- Images
      +-- Documents
      +-- Supporting Evidence
      |
      v
Evidence Analysis
      |
      +-- AI-generated/manipulated image detection
      +-- Image forensics
      +-- OCR
      +-- Document tampering checks
      +-- Metadata checks
      +-- Cross-evidence consistency
      +-- Identity comparison (bonus)
      |
      v
Evidence Fusion / Risk Engine
      |
      +-- Image Authenticity Score
      +-- Document Authenticity Score
      +-- Claim Consistency Score
      +-- Identity result
      +-- Overall Fraud Likelihood
      |
      v
Explainable Investigation Result

INSURANCE-DOMAIN AGNOSTIC RULE

ClaimShield AI must be designed as an insurance-agnostic
digital evidence authenticity and fraud detection system.

Vehicle/accident insurance is only a demonstration example.

Do not build insurance-type-specific detection modules unless
a documented requirement explicitly requires domain-specific
logic.

The core image authenticity, document authenticity, forensic,
and risk-scoring pipelines must work independently of whether
the claim belongs to motor, health, property, travel, life,
commercial, cargo, or another insurance category.

Prefer generic evidence analysis over domain-specific
implementations.

Do not create separate detectors for different insurance types
unless there is a concrete technical requirement that cannot
be solved generically.
```

## 5. Golden implementation rule

**Do not rebuild working functionality unnecessarily.**

ClaimShield AI is a standalone project.

Use the VerifAI repository as a **reference/source of selectively reusable
components**, not as the default architecture.

Rules:
- keep ClaimShield's architecture minimal and purpose-built;
- reuse a VerifAI component only when it solves a real ClaimShield
  requirement and reduces implementation effort;
- do not import passport-specific assumptions into ClaimShield;
- prefer implementing a simpler solution when that is clearer than
  adapting a complex reference component;
- do not copy entire modules, subsystems, or architecture without a
  concrete requirement;
- remove dead code only after the new pipeline is working.

**DON'T DO OVER ENGINEERING.**

## 6. MVP

The minimum successful product should support:

### Image
- Upload image
- AI-generated/manipulated image detection
- Detector confidence
- Basic supporting image-forensic indicators
- Optional visualization of forensic findings
- Image authenticity score

### Document
- Upload PDF/image
- OCR
- Basic metadata analysis
- Tampering indicators
- Basic field extraction

### Risk
- Image authenticity score
- Document authenticity score
- Claim consistency score
- Overall fraud likelihood
- Low/Medium/High result
- Plain-English explanation
- Basic claim/evidence consistency checks (e.g., dates and amounts)

### UI
- Upload claim evidence
- Analyze button
- Results dashboard
- Evidence details
- Explainability

Optional visualizations such as ELA/heatmaps are enhancements,
not blockers for the core MVP.

## 7. Optional / bonus

- Face comparison between ID and selfie
- Advanced cross-document identity consistency
- Image metadata versus claimed timeline
- Synthetic/tampered sample generation
- Suspicious-region heatmap
- Advanced claim-evidence relationships

## 8. Explicit non-goals

Do not introduce:
- microservices
- Kubernetes
- Kafka
- Redis
- complex authentication
- blockchain
- real insurance API integrations
- production-grade enterprise database
- custom deepfake model training from scratch unless absolutely necessary
- LLM agents for tasks that deterministic code can handle
- unnecessary abstraction layers

## 9. Development sequence

1. Establish ClaimShield's minimal project scaffold.
2. Freeze the working Phase 1 baseline.
3. Investigate and select a practical pretrained AI/deepfake image
   detector.
4. Integrate the selected detector into the existing image pipeline.
5. Evaluate whether VerifAI forensic components provide enough value
   to justify selective reuse.
6. Add supporting image forensics where useful.
7. Build generic document analysis (OCR, metadata, tampering indicators).
8. Add cross-evidence consistency checks.
9. Finalize Image Authenticity, Document Authenticity, Claim Consistency,
   and Overall Fraud Likelihood scoring.
10. Build the complete Streamlit claim-evidence workflow.
11. Create representative genuine, AI-generated, manipulated, and
    tampered test/demo cases.
12. Test failure cases and degraded inputs.
13. Remove unused code and dependencies.
14. Prepare the final hackathon demo.

Do not proceed to the next stage merely because it exists in the plan.
Move forward only when the current stage is working reliably.

## 10. Final demo story

A strong demo should tell one coherent story:

> A claimant submits an accident claim. The system analyzes the submitted accident image and supporting document. The image model finds a high probability of synthetic/manipulated content. Document analysis finds one or more tampering inconsistencies. Cross-evidence checks identify a mismatch. The system combines the evidence into an overall fraud likelihood and explains exactly why the claim was flagged.

## 11. Documentation set

Use these files as the project's long-term planning memory:

- `00-MASTER-PLAN.md` — overall blueprint
- `01-PROBLEM-STATEMENT.md` — exact challenge requirements
- `02-GAP-ANALYSIS.md` — VerifAI vs target
- `03-TARGET-ARCHITECTURE.md` — target technical architecture
- `04-FEATURE-REQUIREMENTS.md` — detailed feature checklist
- `05-IMPLEMENTATION-ROADMAP.md` — implementation order
- `06-RISK-ENGINE.md` — scoring/evidence fusion design
- `07-DATASET-AND-TESTING.md` — data and validation strategy
- `08-UI-AND-DEMO.md` — UI and 10-minute demo
- `09-REUSE-MIGRATION-MAP.md` — what to keep/change/remove
- `10-NO-OVERENGINEERING.md` — project guardrails
- `11-FINAL-CHECKLIST.md` — readiness checklist


