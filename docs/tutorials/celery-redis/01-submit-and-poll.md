# 01: Submit And Poll

Date: 2026-04-12

Prompt:

Implement the smallest useful Celery-backed API pair:

- `POST /tutorials/celery-redis/jobs/submit`
- `GET /tutorials/celery-redis/jobs/{task_id}`

What the interviewer or exercise is testing:

- whether you keep the HTTP request short
- whether you return `202 Accepted` and a stable task identifier
- whether you understand that status is read from the result backend later

Minimum success criteria:

- submit returns quickly
- poll exposes `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`
- route contract is clear even before the task body becomes complex

Follow-up questions:

- When should you store job state in your own database instead of only the result backend?
- What should the response shape be if the task does not exist?
