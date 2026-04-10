from fastapi import FastAPI
import asyncio
import time

app = FastAPI(title="fastapi-load-testing", version="0.1.0")
 
 
@app.get("/health")
async def health():
    return {"status": "ok"}
 
 
# TODO lab outline: keep these as comments until you implement the experiments.
#
# Learning goal 1: show what blocks the event loop inside one worker.
# - GET /sleep/blocking
#   - Use `time.sleep(...)`.
#   - Measure how badly unrelated requests suffer under concurrency.
# - GET /sleep/async
#   - Use `await asyncio.sleep(...)`.
#   - Compare p95/p99 and throughput against `/sleep/blocking`.

@app.get("/sleep/blocking")
async def sleep_blocking(seconds: int = 1):
    print(f"/sleep/blocking: Sleeping for {seconds} seconds")
    time.sleep(seconds)
    return {"status": "ok"}

@app.get("/sleep/async")
async def sleep_async(seconds: int = 1):
    print(f"/sleep/async: Sleeping for {seconds} seconds")
    await asyncio.sleep(seconds)
    return {"status": "ok"}


def run_cpu_work(iterations: int) -> int:
    total = 0
    for i in range(iterations):
        total += (i % 97) * (i % 89)
    return total


#
# Learning goal 2: compare CPU work inline versus offloaded.
# - GET /cpu/inline
#   - Run a CPU-heavy loop directly in the request handler.
#   - Confirm that async syntax does not save CPU-bound work.
@app.get("/cpu/inline")
async def cpu_inline(iterations: int = 25_000_000):
    print(f"/cpu/inline: Running CPU-heavy loop for {iterations} iterations")
    checksum = run_cpu_work(iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


# - GET /cpu/to-thread
#   - Offload the same blocking CPU function with `asyncio.to_thread(...)`.
#   - Measure whether responsiveness improves for other requests.
@app.get("/cpu/to-thread")
async def cpu_to_thread(iterations: int = 25_000_000):
    print(f"/cpu/to-thread: Running CPU-heavy loop for {iterations} iterations")
    checksum = await asyncio.to_thread(run_cpu_work, iterations)
    return {"status": "ok", "iterations": iterations, "checksum": checksum}


# Learning goal 3: compare sequential and concurrent fan-out.
# - GET /fanout/sequential
#   - Await each subtask one after another.
@app.get("/fanout/sequential"):
async def 
# - GET /fanout/gather
#   - Run the same subtasks with `asyncio.gather(...)`.
# - Add timestamps so the scheduling difference is visible in logs.
#

# Learning goal 5: simulate bounded shared resources.
# - Add an `asyncio.Semaphore` around a section that represents a DB pool or
#   external service bottleneck.
# - Test what happens when concurrent requests exceed the artificial capacity.
#
# Deployment experiment notes:
# - Re-run the same endpoints with one worker and then with multiple workers.
# - Check which failures come from bad app behavior versus worker-count limits.
 
