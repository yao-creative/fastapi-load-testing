 import asyncio
 
 from fastapi import FastAPI
 
 
 app = FastAPI(title="fastapi-load-testing", version="0.1.0")
 
 
 @app.get("/health")
 async def health():
     return {"status": "ok"}
 
 
 # TODO (you implement): asyncio/load-testing endpoints
 #
 # - Blocking vs non-blocking
 #   - GET /sleep/blocking   -> time.sleep(...)
 #   - GET /sleep/async      -> await asyncio.sleep(...)
 #
 # - CPU-bound inline vs offloaded
 #   - GET /cpu/inline       -> CPU loop inline (blocks event loop within worker)
 #   - GET /cpu/to-thread    -> await asyncio.to_thread(...)
 #
 # - Sync vs async outbound HTTP (to an internal target endpoint)
 #   - GET /upstream/target  -> simple async endpoint with controlled delay
 #   - GET /upstream/sync    -> requests.get("http://127.0.0.1:8000/upstream/target")
 #   - GET /upstream/async   -> await httpx.AsyncClient().get(...)
 #
 # - Sequential vs parallel fan-out
 #   - GET /fanout/sequential -> await subtask(); await subtask(); ...
 #   - GET /fanout/gather     -> await asyncio.gather(...)
 #
 # Optional: resource contention demo
 # - Add an asyncio.Semaphore to simulate a bounded pool (DB pool-like).
 
