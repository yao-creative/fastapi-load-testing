# 03: Progress Reporting

Date: 2026-04-12

Prompt:

Design a long-running task with visible stages such as:

- fetch
- process
- store

What the interviewer or exercise is testing:

- whether you understand that users and operators care about stage, not just final status
- whether you can expose useful progress metadata without inventing a huge workflow engine

Minimum success criteria:

- task state changes during execution
- poll endpoint can report current stage
- failure output preserves the stage where the task died

Follow-up questions:

- When is percentage progress misleading?
- What metadata is actually useful for debugging?
