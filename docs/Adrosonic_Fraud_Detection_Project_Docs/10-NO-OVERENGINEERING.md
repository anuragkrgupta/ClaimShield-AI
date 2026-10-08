# No-Overengineering Rules

## Project rule

> Build the simplest system that reliably satisfies the problem statement.

## 1. No architecture changes without a reason

Before changing architecture, answer:
- What requirement does this solve?
- What bug/problem does it remove?
- Why can't the existing design handle it?

If there is no strong answer, don't change it.

## 2. Prefer reuse

If VerifAI already has a working component and it is relevant:
- reuse it;
- adapt it;
- test it.

Do not rewrite it just because the code is not yours.

## 3. One responsibility, not one file per line of code

Create modules when they represent a real domain responsibility.

Do not create:
- wrappers around wrappers;
- unnecessary factories;
- excessive interfaces;
- one-function abstraction layers.

## 4. No unnecessary infrastructure

Do not add:
- Docker orchestration;
- Kubernetes;
- Redis;
- Kafka;
- microservices;
- message queues;
- cloud databases

unless an actual requirement demands them.

## 5. Model first, infrastructure second

The challenge rewards detection, risk logic, UI, architecture and innovation.

Spend time on:
- detection;
- evidence;
- scoring;
- explanation;
- demo reliability.

Do not spend hackathon time building infrastructure that does not improve those areas.

## 6. Avoid LLM overuse

Use deterministic code for:
- dates;
- amounts;
- IDs;
- exact comparisons;
- thresholds;
- known document fields.

An LLM should not be introduced just because the project is called AI.

## 7. Avoid duplicate logic

There should be one authoritative implementation for:
- risk thresholds;
- score calculation;
- evidence normalization;
- claim representation.

## 8. Fail gracefully

A single broken detector should not destroy the whole claim analysis.

Use:

```text
Detector failed
      ↓
Unavailable signal
      ↓
Continue remaining analysis
```

## 9. Don't optimize prematurely

First:
- correct;
- understandable;
- demonstrable.

Then optimize only if profiling shows a real bottleneck.

## 10. Don't refactor during the critical path

If working code solves the requirement:
- leave it;
- add a test;
- move forward.

Clean it after the MVP works.

## 11. Complexity budget

For every new component ask:

```text
Does this improve:
A. detection?
B. explainability?
C. reliability?
D. demo?
E. required architecture?
```

If none apply, it probably does not belong in the MVP.

## 12. Definition of done

A feature is done when:
- it works;
- it has a test/sample;
- its output is understandable;
- it does not break existing features.

Not when it has the most sophisticated architecture.
