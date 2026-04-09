# Lumina Sprint 1 - Static Pipeline PoC

This sprint implements a 2-node split inference proof-of-concept with dynamic assignment:

- Tracker assigns split points based on node capability and heartbeat.
- Node A loads the model and executes head layers up to assigned `split_layer`.
- Node A serializes hidden states and sends them to Node B.
- Node B executes tail layers and returns the next token.
- Node A loops token-by-token to produce multi-token generation.

## Why this matches Sprint 1

This demonstrates the critical milestone: intercepting an intermediate forward pass tensor, serializing/transmitting it over a standard API, and completing generation on a second node.

## Project layout

- `node_a.py`: Prompt entrypoint (`/generate`) and head-layer execution.
- `node_b.py`: Tail-layer execution (`/forward_tail`).
- `lumina_sprint1/tensor_codec.py`: Tensor <-> base64 bytes serialization.
- `lumina_sprint1/schemas.py`: Shared request/response models.
- `tracker.py`: Assignment and rebalance service.
- `docker-compose.yml`: Tracker + 2-node local deployment.

## Prerequisites

- Python 3.11+
- Optional: Docker + Docker Compose

## Local run (2 terminals)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start tracker:

```bash
uvicorn tracker:app --host 0.0.0.0 --port 8003
```

3. Start Node B:

```bash
uvicorn node_b:app --host 0.0.0.0 --port 8002
```

4. Start Node A:

```bash
export NODE_B_URL=http://localhost:8002
export TRACKER_URL=http://localhost:8003
uvicorn node_a:app --host 0.0.0.0 --port 8001
```

5. Test generation:

```bash
curl -X POST http://localhost:8001/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Lumina is","max_new_tokens":1}'
```

## Docker run

```bash
docker compose up --build
```

Then call:

```bash
curl -X POST http://localhost:8001/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Lumina is","max_new_tokens":1}'
```

## Run tests

```bash
pytest -q
```

## Notes and constraints

- Uses `sshleifer/tiny-gpt2` by default to keep Sprint 1 lightweight.
- Node B predicts one token per call; Node A performs the autoregressive loop.
- Dynamic split assignment uses a lightweight in-memory tracker policy.

## Next Sprint 1 extension ideas

- Add iterative token generation loop across nodes.
- Add gRPC transport as an alternate channel (same tensor payload contract).
- Add latency metrics (`encode_ms`, `transfer_ms`, `decode_ms`, `tail_ms`).
