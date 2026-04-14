# 05: Queue Routing And Isolation

Date: 2026-04-12

Prompt:

Explain how you would separate light jobs from heavy jobs.

What the interviewer or exercise is testing:

- whether you understand queue starvation
- whether you can reason about worker ownership and workload isolation

Minimum success criteria:

- define at least two queues
- describe which tasks belong in each queue
- describe which workers consume which queues

Follow-up questions:

- What breaks if everything stays on the default queue?
- How do you prove that heavy backlog is no longer hurting light jobs?
