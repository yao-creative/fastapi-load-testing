# 02: Retries And Idempotency

Date: 2026-04-12

Prompt:

Design a task that talks to a flaky dependency and may need retry.

What the interviewer or exercise is testing:

- whether you know retries are for transient failures
- whether you understand duplicate-safe side effects
- whether you can explain why task id is not enough as a business dedupe key

Minimum success criteria:

- task retries on transient failure
- side effects are protected by an idempotency key or dedupe record
- logs or state make attempt count visible

Follow-up questions:

- What happens if the task partially succeeds before raising?
- How do you prevent duplicate emails, duplicate indexing, or duplicate writes?
