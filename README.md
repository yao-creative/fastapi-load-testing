 ## fastapi-load-testing (bare minimum)
 
 Minimal scaffolding:
 - FastAPI app managed by `uv`
 - Dockerized API
 - Dockerized Locust runner + UI
 
 Endpoint implementations for asyncio variations are intentionally left to you (see TODO stubs in `app/main.py`).
 
 ## Local (uv)
 - Install deps and create a venv:
 
 ```bash
 uv sync
 ```
 
 - Run the API:
 
 ```bash
 uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
 ```
 
 - Smoke test:
 
 ```bash
 curl http://localhost:8000/health
 ```
 
 ## Docker (API + Locust)
 - Start API + Locust UI:
 
 ```bash
 docker compose up --build
 ```
 
 - Open Locust UI at `http://localhost:8089`
   - Host should be `http://api:8000`
  - (Tip) You can leave the Host field empty; compose sets `LOCUST_HOST=http://api:8000`
 
 ## Next steps (you implement)
 - Add endpoint variants in `app/main.py` (blocking vs async sleep, cpu inline vs to_thread, sync vs async http, fanout gather vs sequential).
 - Add matching Locust tasks in `loadtest/locustfile.py`.
 - Optionally add a multi-worker profile using gunicorn + `uvicorn.workers.UvicornWorker`.
 
