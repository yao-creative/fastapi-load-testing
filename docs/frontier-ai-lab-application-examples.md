# Frontier AI Lab Application Examples

Date: 2026-04-10

Goal: connect each tutorial in this repo to the kinds of systems and workloads that show up in real AI serving, evaluation, retrieval, and agent orchestration stacks.

This file is not claiming that every frontier AI lab uses the exact same implementation. The point is narrower:
- each asyncio pattern in this repo has a very direct analog in modern LLM serving and agent systems
- if you understand the toy exercise well, you can usually recognize the same pressure in a production AI stack


## 00: asyncio sequence diagrams

File:
- `docs/tutorials/async/00-asyncio-sequence-diagrams.md`

Real-world AI lab analogs:
- A chat or agent request that goes through retrieval, reranking, safety checks, tool calls, and final generation.
- A model-serving gateway that orchestrates several internal services before returning one response.
- A multi-model composition service, such as a router that calls one model for classification and another for generation.

Why this maps:
- Ray Serve explicitly positions itself for model composition and multi-model serving, not just one-model inference.
- vLLM documents continuous batching, prefix caching, parallelism modes, tool calling, and reasoning parsers, all of which are easier to reason about once you can visualize task lifecycles and handoff points.

Sample code sketch:

```python
@app.post("/agent/answer")
async def answer(question: str):
    retrieved_docs = await retrieve(question)
    safety = await run_safety_check(question)
    final_prompt = build_prompt(question, retrieved_docs, safety)
    answer = await call_model(final_prompt)
    return {"answer": answer, "safety": safety}
```


## 01: `/tutorials/async/sleep/blocking` vs `/tutorials/async/sleep/async`

File:
- `docs/tutorials/async/01-experiment-sleep-blocking-vs-async.md`

Real-world AI lab analogs:
- An orchestration API waiting on remote model calls over HTTP.
- A tool-using agent waiting on web search, vector retrieval, or sandbox execution.
- A gateway that streams tokens from a model server while still needing to handle unrelated requests.

What the lesson becomes in practice:
- If the handler is waiting on network I/O to a model API or retrieval system, it should yield cleanly.
- If you accidentally call a blocking client or blocking helper in the request path, unrelated traffic on that worker stalls for no good reason.

Sample code sketch:

```python
@app.post("/chat/async")
async def chat_async(prompt: str):
    result = await async_model_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )
    return {"text": result.output_text}


@app.post("/chat/blocking")
async def chat_blocking(prompt: str):
    # Bad shape: this sync SDK call blocks the event loop worker.
    result = blocking_model_client.generate(prompt)
    return {"text": result.text}
```


## 02: `/tutorials/async/cpu/inline` vs `/tutorials/async/cpu/to-thread`

File:
- `docs/tutorials/async/02-experiment-cpu-inline-vs-to-thread.md`

Real-world AI lab analogs:
- PDF parsing, OCR preprocessing, or image resizing before sending data to a model.
- Synchronous tokenization, chunking, or schema validation around an otherwise async request path.
- Expensive post-processing such as ranking, JSON transformation, or local scoring logic wrapped around remote inference.

What the lesson becomes in practice:
- Async syntax does not save CPU-heavy preprocessing or post-processing.
- If you keep CPU-bound Python inline in the request handler, the event loop is still stuck.
- `to_thread(...)` can help keep the server responsive when you must call sync helpers, even if it is not a universal performance fix.

Sample code sketch:

```python
def parse_and_chunk_pdf(file_bytes: bytes) -> list[str]:
    pages = expensive_pdf_parse(file_bytes)
    return chunk_pages(pages)


@app.post("/ingest/inline")
async def ingest_inline(file_bytes: bytes):
    chunks = parse_and_chunk_pdf(file_bytes)
    await embed_and_store(chunks)
    return {"chunks": len(chunks)}


@app.post("/ingest/to-thread")
async def ingest_to_thread(file_bytes: bytes):
    chunks = await asyncio.to_thread(parse_and_chunk_pdf, file_bytes)
    await embed_and_store(chunks)
    return {"chunks": len(chunks)}
```


## 03: `/tutorials/async/fanout/sequential` vs `/tutorials/async/fanout/gather`

File:
- `docs/tutorials/async/03-experiment-fanout-sequential-vs-gather.md`

Real-world AI lab analogs:
- Parallel retrieval across multiple indices or stores, such as semantic search plus keyword search plus metadata lookup.
- Running several lightweight guardrails at once: moderation, PII detection, prompt classification, citation fetch, or policy checks.
- Querying multiple candidate tools or model endpoints in parallel before choosing the final answer path.

What the lesson becomes in practice:
- If the subtasks mostly wait on I/O, parallel fan-out materially lowers one-request latency.
- This is exactly the kind of win you want in agent orchestration, RAG, and model gateway code.

Sample code sketch:

```python
@app.post("/rag/search")
async def rag_search(query: str):
    vector_hits, keyword_hits, graph_hits = await asyncio.gather(
        search_vector_index(query),
        search_keyword_index(query),
        search_knowledge_graph(query),
    )
    merged = merge_results(vector_hits, keyword_hits, graph_hits)
    return {"results": merged}
```


## 04: producer-consumer pattern

File:
- `docs/tutorials/async/06-experiment-producer-consumer-asyncio-queue.md`

Real-world AI lab analogs:
- Submit a document-ingestion job now, process it later, then poll for status.
- Kick off eval runs, prompt regression suites, or synthetic-data generation outside the request lifecycle.
- Queue long-running media generation or report-generation jobs behind a broker and worker pool.

What the lesson becomes in practice:
- The HTTP request should often end with job acceptance, not with all downstream work completed.
- This pattern shows up whenever the user does not need the result immediately, or when the work is too heavy to keep inside a latency-sensitive request path.

Sample code sketch:

```python
@app.post("/eval-runs")
async def create_eval_run(dataset_id: str):
    run_id = str(uuid.uuid4())
    await broker.enqueue({"run_id": run_id, "dataset_id": dataset_id})
    return {"status": "accepted", "run_id": run_id}


@app.get("/eval-runs/{run_id}")
async def get_eval_run(run_id: str):
    return await run_store.get(run_id)
```


## 05: bounded resource with `asyncio.Semaphore`

File:
- `docs/tutorials/async/05-experiment-bounded-resource-semaphore.md`

Real-world AI lab analogs:
- Cap in-flight requests against a rate-limited model API.
- Protect a shared GPU-backed inference service from too many concurrent requests.
- Limit concurrent access to a fragile vector database, reranker, or retrieval backend.

What the lesson becomes in practice:
- OpenAI exposes organization-level and project-level rate limits, including request, token, and batch queue limits.
- Semaphore-like gates are the app-side control you use so your service does not smash into those limits or overload a downstream dependency before the provider throttles you.

Sample code sketch:

```python
model_api_slots = asyncio.Semaphore(8)


@app.post("/guardrailed-answer")
async def guardrailed_answer(prompt: str):
    async with model_api_slots:
        result = await async_model_client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
    return {"text": result.output_text}
```


## 06: producer-consumer with `asyncio.Queue`

File:
- `docs/tutorials/async/06-experiment-producer-consumer-asyncio-queue.md`

Real-world AI lab analogs:
- In-process ingestion of uploaded documents before chunking, embedding, and indexing.
- Micro-batching or staged processing before handing work to a model-serving backend.
- A small per-worker backlog that smooths bursts before consumers drain jobs.

What the lesson becomes in practice:
- Ray Serve's dynamic request batching literally queues requests, forms a batch, runs evaluation on the batch, then splits results back to individual responses.
- OpenAI vector-store file and file-batch APIs are also a useful mental analog: ingestion is asynchronous work with queueing, polling, and eventual readiness.

Sample code sketch:

```python
ingest_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)


async def ingest_worker():
    while True:
        job = await ingest_queue.get()
        try:
            chunks = await asyncio.to_thread(parse_document, job["file_bytes"])
            embeddings = await embed_chunks(chunks)
            await store_embeddings(job["doc_id"], embeddings)
        finally:
            ingest_queue.task_done()


@app.post("/documents")
async def upload_document(doc_id: str, file_bytes: bytes):
    await ingest_queue.put({"doc_id": doc_id, "file_bytes": file_bytes})
    return {"status": "queued", "doc_id": doc_id}
```


## 07: timeouts and cancellation

File:
- `docs/tutorials/async/04-experiment-timeout-and-cancellation.md`

Real-world AI lab analogs:
- A user closes the browser tab while an agent is still running retrieval and tool calls.
- A chat request hits an internal latency budget and must stop waiting on slow sub-operations.
- A long-running reasoning task is moved to an asynchronous job mode instead of tying up the live request.

What the lesson becomes in practice:
- Long-running reasoning workloads are exactly the use case OpenAI's background mode is designed for: asynchronous execution with polling rather than keeping one request open indefinitely.
- For normal online paths, you still need deadlines and correct cancellation cleanup so work does not leak when the request times out.

Sample code sketch:

```python
@app.post("/agent/live")
async def live_agent(question: str):
    try:
        async with asyncio.timeout(8):
            answer = await run_agent(question)
            return {"status": "ok", "answer": answer}
    except TimeoutError:
        return {"status": "timeout"}


@app.post("/agent/background")
async def background_agent(question: str):
    job_id = str(uuid.uuid4())
    await broker.enqueue({"job_id": job_id, "question": question})
    return {"status": "accepted", "job_id": job_id}
```


## 08: `gather(...)` vs `TaskGroup` failure propagation

File:
- `docs/tutorials/async/07-experiment-gather-vs-taskgroup-failure-propagation.md`

Real-world AI lab analogs:
- An agent request fans out to retrieval, tool planning, safety checks, and output formatting, and one branch fails.
- A multi-model pipeline where one stage is mandatory and failure should cancel sibling work.
- A best-effort enrichment workflow where partial results might still be useful.

What the lesson becomes in practice:
- In agent systems, failure semantics are part of the product behavior, not just an implementation detail.
- Python's `TaskGroup` is relevant when one failing branch should cancel the rest and exit in a structured way.
- `gather(...)` can still be useful when you want different fan-in behavior, but you should choose it deliberately.

Sample code sketch:

```python
async def run_agent_branches(question: str):
    async with asyncio.TaskGroup() as tg:
        retrieval_task = tg.create_task(retrieve(question))
        policy_task = tg.create_task(check_policy(question))
        tool_plan_task = tg.create_task(plan_tools(question))

    return {
        "docs": retrieval_task.result(),
        "policy": policy_task.result(),
        "plan": tool_plan_task.result(),
    }
```


## 09: shared state race and `asyncio.Lock`

File:
- `docs/tutorials/async/08-experiment-shared-state-race-and-lock.md`

Real-world AI lab analogs:
- Per-process prompt-cache bookkeeping.
- In-memory counters for token budgets, request budgets, or ad hoc rate limiting.
- Deduplication state for work that should only happen once per worker, such as a lazy local initialization path.

What the lesson becomes in practice:
- Even if your FastAPI worker is single-threaded at the event-loop level, coroutine interleavings can still corrupt shared state.
- `asyncio.Lock` can protect in-process correctness, but it will not coordinate across multiple Uvicorn workers. For shared correctness across workers, you need an external system.

Sample code sketch:

```python
budget_lock = asyncio.Lock()
remaining_tokens = {"team-a": 100_000}


@app.post("/budgeted-call")
async def budgeted_call(team_id: str, estimated_tokens: int, prompt: str):
    async with budget_lock:
        if remaining_tokens[team_id] < estimated_tokens:
            return {"status": "rejected", "reason": "budget_exceeded"}
        remaining_tokens[team_id] -= estimated_tokens

    result = await async_model_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )
    return {"status": "ok", "text": result.output_text}
```


## 10: leveling rubric

File:
- `docs/asyncio-leveling-rubric.md`

Real-world AI lab analogs:
- Debug why one LLM gateway has great p50 but terrible p99 under mixed traffic.
- Decide whether a new capability belongs in the live request path, a background job, or an external worker system.
- Review a teammate's async design and identify overload, cancellation, or shared-state risks before they hit production.

What the lesson becomes in practice:
- AI infra interviews and senior backend work usually test judgment on these exact boundaries: latency vs throughput, async vs threads vs workers, bounded concurrency, and failure cleanup.

Sample code sketch:

```python
def review_checklist(endpoint_code: str) -> list[str]:
    findings = []
    if "time.sleep(" in endpoint_code:
        findings.append("Blocking sleep inside async path")
    if "asyncio.gather(" in endpoint_code and "Semaphore" not in endpoint_code:
        findings.append("Check for unbounded fan-out")
    if "create_task(" in endpoint_code and "finally" not in endpoint_code:
        findings.append("Check cancellation and cleanup")
    return findings
```


## Source Notes

Examples in this file were anchored to current docs from real AI platforms and serving stacks:

- OpenAI Batch API: asynchronous grouped jobs for evaluations, classification, embeddings, and other offline workloads
- OpenAI Background mode: asynchronous long-running model tasks with polling
- OpenAI Rate limits and project rate limits: request/token limits and queue limits that motivate app-side concurrency controls
- OpenAI Retrieval / vector store file batches: asynchronous ingestion and indexing mental model
- Ray Serve: dynamic request batching, multi-model serving, and model composition
- vLLM: continuous batching, prefix caching, distributed inference, and OpenAI-compatible serving

Reference URLs:
- https://developers.openai.com/api/docs/guides/batch
- https://developers.openai.com/api/docs/guides/background
- https://developers.openai.com/api/docs/guides/rate-limits
- https://platform.openai.com/docs/api-reference/project-rate-limits
- https://platform.openai.com/docs/api-reference/vector-stores-file-batches
- https://platform.openai.com/docs/guides/retrieval
- https://docs.ray.io/en/latest/serve/advanced-guides/dyn-req-batch.html
- https://docs.ray.io/en/latest/serve/index.html
- https://docs.vllm.ai/
- https://docs.python.org/3/library/asyncio-task.html
- https://docs.python.org/3/library/asyncio-sync.html
