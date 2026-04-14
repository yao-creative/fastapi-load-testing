# 06: Periodic Jobs And Beat

Date: 2026-04-12

Prompt:

Design a scheduled task flow using `celery beat`.

What the interviewer or exercise is testing:

- whether you know beat is a scheduler, not a worker
- whether you can describe recurring maintenance or refresh work cleanly

Minimum success criteria:

- scheduled publish path is clear
- worker execution path is separate
- overlap policy is discussed

Follow-up questions:

- What happens if beat is running but workers are down?
- How do you prevent overlapping scheduled runs?
