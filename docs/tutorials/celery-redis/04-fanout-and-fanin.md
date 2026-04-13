# 04: Fan-Out And Fan-In

Date: 2026-04-12

Prompt:

Model a workflow where one user request causes several child tasks to run in parallel, then combines their results.

What the interviewer or exercise is testing:

- whether you know the difference between one task and one workflow
- whether you can explain `group`, `chain`, and `chord` at a practical level

Minimum success criteria:

- child tasks can run independently
- parent or callback logic waits for all required children
- result aggregation logic is explicit

## Sequence diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Broker as Redis broker
    participant W1 as worker A
    participant W2 as worker B
    participant W3 as worker C
    participant Callback as aggregate callback

    Client->>API: POST /jobs/fanout
    API->>Broker: publish group/chord
    API-->>Client: 202 Accepted + workflow id
    par child execution
        Broker-->>W1: child task 1
        W1->>W1: compute partial result
    and
        Broker-->>W2: child task 2
        W2->>W2: compute partial result
    and
        Broker-->>W3: child task 3
        W3->>W3: compute partial result
    end
    Broker->>Callback: enqueue callback after all children finish
    Callback->>Callback: merge child outputs
```

## Implementation hints

- Start with small independent child tasks that return deterministic values.
- Decide whether you want a `group`, `chain`, or `chord` before writing the route.
- Return both the parent workflow id and the child task ids if that helps debugging.
- Define failure policy up front: fail fast, partial results, or compensating action.
- Do not use fan-out for tiny work items unless the queueing overhead is worth it.

Follow-up questions:

- What should happen if one child fails?
- When should you prefer one larger task instead of many small tasks?
