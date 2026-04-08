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
 


## Reference Articles:
1. https://www.techbuddies.io/2026/01/05/top-7-fastapi-asyncio-best-practices-for-non-blocking-web-apis/#:~:text=Before%20I%20started%20applying%20any,schedules%20all%20your%20async%20work.
2. https://dev.to/imsushant12/asyncio-architecture-in-python-event-loops-tasks-and-futures-explained-4pn3
3. https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e
4. https://www.youtube.com/watch?v=esIEW0aEKqk 