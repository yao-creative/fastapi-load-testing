# 08: Celery Vs Redis Streams

Date: 2026-04-12

Prompt:

Compare Celery task queues with Redis Streams consumer groups.

What the interviewer or exercise is testing:

- whether you choose tools by workload shape instead of habit
- whether you can distinguish task execution from event-log processing

Minimum success criteria:

- explain when Celery is the better fit
- explain when Streams are the better fit
- discuss acknowledgements, replay, and pending work at a practical level

Follow-up questions:

- Why might one platform use both?
- Which one is easier to reason about for “run this job later” versus “process this event log”?
