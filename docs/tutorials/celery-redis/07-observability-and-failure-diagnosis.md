# 07: Observability And Failure Diagnosis

Date: 2026-04-12

Prompt:

Explain how you would debug a stuck or slow Celery system.

What the interviewer or exercise is testing:

- whether you think operationally about queues, active tasks, retries, and backlog
- whether you can distinguish broker issues from worker issues from dependency issues

Minimum success criteria:

- mention queue depth
- mention active versus scheduled versus failed tasks
- mention correlation of task id across logs and monitoring

Follow-up questions:

- What does a growing queue with idle workers suggest?
- What does a stable queue with slow completions suggest?
