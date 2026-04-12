# 04: Fan-Out And Fan-In

Date: 2026-04-12

Prompt:

Model a workflow where one user request causes several child tasks to run in parallel, then combines their results.

What the interviewer or exercise is testing:

- whether you know the difference between one task and one workflow
- whether you can explain `group`, `chain`, and `chord` at a practical level

Minimum success criteria:

- child tasks can run independently
- parent or callback logic waits for all required children
- result aggregation logic is explicit

Follow-up questions:

- What should happen if one child fails?
- When should you prefer one larger task instead of many small tasks?
