# Agent Notes

## Generic 

- I'd like for the worktrees to ALWAYS be created withing .agents/.worktrees/<worktree-branch-name>
- At the end of every response always critique my code and give me a two sentence next step on what I could improve. I want to be compared against the top 1% frontier startups practices.

## Tutorial Documentation Skeleton

When adding a new tutorial track to this repo, prefer a documentation-first skeleton before implementing code.

Expected structure:

- `00-*.md` is the overview
- `01-*.md` and onward are the real exercises, prompts, or interview-style questions

The `00` overview should contain:

- the runtime mental model
- sequence diagrams
- key terminology and hierarchy
- how the pattern maps to real systems such as frontier labs or production companies
- the suggested route or implementation sequence

The numbered exercise docs should contain:

- the exercise or interview prompt
- what the exercise is testing
- minimum success criteria
- follow-up questions

Do not make `00` just another exercise. `00` is the orientation and framing doc.


## Tutorial Router Style

When a tutorial track is meant for learning rather than for shipping a completed example, prefer comment-form routers.

That means:

- create the router file under `app/api`
- register the router so the tutorial track exists in project structure
- leave the endpoints unimplemented
- use comments to explain learning goals, route sequence, and implementation guidance

The router file should act as a scaffold, not an answer key.

Suggested comment content:

- overall learning goal for the track
- which endpoints should be implemented first
- what each endpoint is meant to teach
- implementation order and constraints
- reminder that the file is intentionally left unimplemented

Example shape:

- `app/api/tutorials_<topic>.py`
- `router = APIRouter(prefix=\"/tutorials/<topic>\", tags=[...])`
- comments describing `00` overview and `01+` exercise route ideas


## Current Celery + Redis Convention

For the Celery + Redis tutorial track in this repo:

- docs live under `docs/tutorials/celery-redis/`
- `00-overview.md` is the overview
- `01` through `08` are the exercises
- `app/api/tutorials_celery_redis.py` is intentionally comment-only scaffolding

If this track is implemented later, keep the doc numbering and route contract stable so the learning flow does not drift.
