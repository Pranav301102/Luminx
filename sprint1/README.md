# Lumina Sprint 1 - Static Pipeline PoC

This sprint implements a 2-node static split inference proof-of-concept:

- Node A loads the model and executes head layers up to `SPLIT_LAYER`.
- Node A serializes hidden states and sends them to Node B.
- Node B executes tail layers and returns the next token.
- Node A merges that token with the original prompt and returns text.

## Why this matches Sprint 1

This demonstrates the critical milestone: intercepting an intermediate forward pass tensor, serializing/transmitting it over a standard API, and completing generation on a second node.

## Project layout

- `node_a.py`: Prompt entrypoint (`/generate`) and head-layer execution.
- `node_b.py`: Tail-layer execution (`/forward_tail`).
- `lumina_sprint1/tensor_codec.py`: Tensor <-> base64 bytes serialization.
- `lumina_sprint1/schemas.py`: Shared request/response models.
- `docker-compose.yml`: 2-node local deployment.

## Prerequisites

- Python 3.11+
- Optional: Docker + Docker Compose

## Local run (2 terminals)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start Node B:

```bash
uvicorn node_b:app --host 0.0.0.0 --port 8002
```

3. Start Node A:

```bash
export NODE_B_URL=http://localhost:8002
uvicorn node_a:app --host 0.0.0.0 --port 8001
```

4. Test generation:

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

## Notes and constraints

- Uses `sshleifer/tiny-gpt2` by default to keep Sprint 1 lightweight.
- Current PoC returns exactly one next token from Node B.
- `max_new_tokens` is accepted in APIs for future extension but not yet looped token-by-token.

## Next Sprint 1 extension ideas

- Add iterative token generation loop across nodes.
- Add gRPC transport as an alternate channel (same tensor payload contract).
- Add latency metrics (`encode_ms`, `transfer_ms`, `decode_ms`, `tail_ms`).
