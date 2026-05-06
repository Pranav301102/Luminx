# Lumina — Distributed Split Inference

Lumina runs a large language model across three physically separate machines by splitting its transformer layers between them. A **Tracker** service dynamically recalculates the optimal split boundaries at runtime based on each node's available VRAM, distributing the assignment via a versioned REST API.

## How It Works

```
Client
  │
  ▼ POST /generate
┌──────────────────────────────┐
│  Node A — Head  (port 8001)  │  layers  0 →  8  (tokenize + embed)
└──────────────┬───────────────┘
               │ POST /forward_mid  (base64 hidden states)
               ▼
┌──────────────────────────────┐
│  Node B — Mid   (port 8002)  │  layers  9 → 18  (relay node)
└──────────────┬───────────────┘
               │ POST /forward_tail (base64 hidden states)
               ▼
┌──────────────────────────────┐
│  Node C — Tail  (port 8004)  │  layers 19 → 27 + ln_f + lm_head
│  Returns next token (b64)    │
└──────────────────────────────┘

All three nodes register and heartbeat with:

┌──────────────────────────────┐
│  Tracker        (port 8003)  │
│  Monitors node health        │
│  Computes split boundaries   │
│  Exposes /assignment         │
└──────────────────────────────┘
```

Split boundaries are recalculated on every heartbeat proportional to each node's VRAM:
```
split_layer_a = round((vram_a / total_vram) * total_layers)
split_layer_b = split_layer_a + round((vram_b / total_vram) * total_layers)
```

Default cloud split: **9 / 10 / 9** across 28 layers (Qwen2.5-1.5B-Instruct).

### Memory-Aware Model Loading

Each node loads **only the layers it will execute** — unused weights are never materialized. On CPU, `model_adapter._load_slice_cpu` builds a full model skeleton on PyTorch's `meta` device (zero RAM), then reads only the needed tensors directly from HuggingFace safetensors shards via `safe_open`, inserting them in-place with `load_state_dict(assign=True)`.

```
Node A loads:  embed_tokens + layers  0– 8               (~⅓ model)
Node B loads:  layers  9–18                               (~⅓ model)
Node C loads:  layers 19–27 + final norm + lm_head        (~⅓ model)
```

On CUDA, the standard `device_map='auto'` path is used.

**Supported architectures:** Qwen2 / Qwen2-MoE · GPT-2 family · Phi-3 / Phi-4 Mini (auto-detected from model config).

### Background Heartbeat

Each node starts a **daemon thread on startup** that sends a heartbeat to the Tracker every **20 seconds**, independent of inference traffic. This ensures the Tracker's liveness registry stays current even during idle periods.

## Project Layout

```
lumina_sprint1/
├── config.py           # pydantic-settings config (env vars / .env)
├── model_adapter.py    # safetensors slice loader, layer helpers, Qwen2 RoPE fix
├── schemas.py          # shared Pydantic request/response models
├── tensor_codec.py     # tensor ↔ base64 serialization
├── tracker_core.py     # AssignmentManager — split logic + request traces
└── discovery.py        # service discovery helpers

node_a.py                    # Head node  — POST /generate
node_b.py                    # Mid node   — POST /forward_mid
node_c.py                    # Tail node  — POST /forward_tail
tracker.py                   # Tracker service
docker-compose.cloud1.yml    # Cloud machine 1: Tracker + Node A + nginx frontend
docker-compose.cloud2.yml    # Cloud machine 2: Node C (tail, ARM t4g.large)
docker-compose.local.yml     # Local/on-prem machine: Node B (mid, NVIDIA GPU)
docker/Dockerfile            # Single image used by all services
lumina-frontend-main/
├── nginx.conf               # nginx reverse-proxy config (proxies /generate, /nodes/, etc.)
└── src/                     # React + Vite dashboard
deploy-ec2/                  # EC2 Terraform + deploy scripts
terraform/                   # AWS Fargate production deployment
scratch/                     # Test scripts (test_qwen.py, test_load.py, etc.)
```

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- `safetensors` and `huggingface_hub` Python packages (in `requirements.txt`)

## Running Locally (single machine, tiny model)

```bash
pip install -r requirements.txt
# Uses sshleifer/tiny-gpt2 by default — lightweight pipeline smoke-test
docker compose up --build
```

Test:
```bash
curl -X POST http://localhost:8001/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Lumina is", "max_new_tokens": 20}'
```

Run tests:
```bash
pytest -q
```

## Cloud Deployment (3-machine split, Qwen2.5-1.5B)

The production topology splits across three machines:

| Machine | Compose file | Services | Notes |
|---------|-------------|----------|-------|
| Cloud 1 (ARM t4g.large) | `docker-compose.cloud1.yml` | Tracker · Node A · nginx frontend | `NODE_B_URL`, `NODE_C_URL` injected at deploy time |
| Cloud 2 (ARM t4g.large) | `docker-compose.cloud2.yml` | Node C (tail) | `TRACKER_URL` injected |
| Local / on-prem (NVIDIA) | `docker-compose.local.yml`  | Node B (mid)  | `TRACKER_URL`, `NODE_C_URL` injected |

**Deploy Cloud 1 (head + tracker + frontend):**
```bash
NODE_B_URL=http://<local_public_ip>:8002 \
NODE_C_URL=http://<cloud2_ip>:8004 \
docker compose -f docker-compose.cloud1.yml up -d --build
```

**Deploy Cloud 2 (tail):**
```bash
TRACKER_URL=http://<cloud1_ip>:8003 \
docker compose -f docker-compose.cloud2.yml up -d --build
```

**Deploy Node B locally (mid):**
```bash
TRACKER_URL=http://<cloud1_ip>:8003 \
NODE_C_URL=http://<cloud2_ip>:8004 \
docker compose -f docker-compose.local.yml up -d --build
```

Or use the PowerShell helper on Windows:
```powershell
.\start-node-b.ps1
```

> **Note:** First startup downloads Qwen2.5-1.5B from HuggingFace (~3 GB). Health check `start_period` is set to **600 s** to accommodate this. `HF_HUB_ENABLE_HF_TRANSFER=1` is set for faster downloads.

## Configuration

All settings are read from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `microsoft/Phi-4-mini-instruct` | HuggingFace model |
| `SPLIT_LAYER_A` | `10` | Head/mid boundary (Node A runs layers 0→A) |
| `SPLIT_LAYER_B` | `21` | Mid/tail boundary (Node B runs layers A→B) |
| `SPLIT_LAYER` | `10` | Backward-compat alias for `SPLIT_LAYER_A` |
| `NODE_B_URL` | `http://localhost:8002` | Node B address (used by Node A) |
| `NODE_C_URL` | `http://localhost:8004` | Node C address (used by Node B) |
| `TRACKER_URL` | `http://localhost:8003` | Tracker address |
| `ENABLE_DYNAMIC_SPLIT` | `true` | Let tracker override split boundaries |
| `NODE_A_ID` / `NODE_B_ID` / `NODE_C_ID` | `node-a/b/c` | Node identifiers |
| `HEARTBEAT_TIMEOUT_SEC` | `30` | Stale threshold (120 s in cloud compose) |

## API Reference

### Node A (Head) — port 8001
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, model, split_layer_a/b, loaded layer count |
| `POST` | `/generate` | Generate text — `{"prompt": "...", "max_new_tokens": 20}` |

### Node B (Mid) — port 8002
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, model, split_layer_a/b, loaded layer count |
| `POST` | `/forward_mid` | Receive hidden states from Node A, forward output to Node C |

### Node C (Tail) — port 8004
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, model, split_layer_b, loaded layer count |
| `POST` | `/forward_tail` | Run final layers, return next token as base64 tensor |

### Tracker — port 8003
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/assignment` | Current split boundaries + version |
| `GET` | `/nodes/list` | All registered nodes and their status |
| `GET` | `/assignments/current` | Layer ranges assigned per node |
| `POST` | `/register` | Register a node with VRAM + layer capacity |
| `POST` | `/heartbeat` | Refresh a node's last-seen timestamp |
| `POST` | `/lease/renew` | Renew a node's lease |
| `GET` | `/requests/traces` | Recent request history with timing |
| `GET` | `/requests/trace/{id}` | Single request trace |
| `POST` | `/requests/start` | Record request start |
| `POST` | `/requests/update` | Update request status |

## Architecture Diagram

```
                                   ┌───────────────────┐
                                   │  Tracker :8003     │
                                   │  VRAM split        │
                                   │  Heartbeat / trace │
                                   └─────────┬──────────┘
         heartbeat ▲               ▲ heartbeat│ heartbeat ▲
                   │               │          │           │
┌──────────────────┴──┐  /forward_mid  ┌──────┴──────────┐  /forward_tail  ┌──────────────────┐
│  Node A  :8001 (Head)│ ─────────────▶│ Node B :8002 (Mid)│ ──────────────▶│ Node C :8004 (Tail)│
│  layers 0–8          │               │  layers 9–18      │                │  layers 19–27      │
│  tokenize + embed    │               │  relay node       │                │  ln_f + lm_head    │
└──────────────────────┘               └───────────────────┘                └──────────┬─────────┘
        ▲  POST /generate                                                               │ next token
        │                                                                               │
   Client / Browser ◀──────────────────────────────────────────────────────────────────┘
        ▲
   React Frontend :80 (nginx reverse-proxy)
```

## Model Notes

- **Cloud demo:** `Qwen/Qwen2.5-1.5B-Instruct` — 28 layers, 1.5B params, coherent output. Split 9/10/9 by default.
- **Local smoke-test:** `sshleifer/tiny-gpt2` — 2 layers, ~50 MB, validates the pipeline only.
- Change via `MODEL_NAME` env var. The `model_adapter` auto-detects architecture from the model config.
- Supported: **Qwen2 / Qwen2-MoE**, **GPT-2 family**, **Phi-3 / Phi-4 Mini**.

## Frontend

React dashboard (Vite) with five pages:

| Page | Description |
|------|-------------|
| Chat | Type a prompt and generate text via the live API |
| Health | Node A/B/C + Tracker status, model name, layer counts |
| Cluster | Live node table — CPU%, RAM, VRAM, latency, active connections, sharing topology; summary cards for total/active/inactive nodes |
| Trace | Request history with per-request duration and assigned nodes |
| Logs | Client-side activity log (polling events, API errors); persisted to `localStorage` (max 150 entries, UUID fallback for non-HTTPS); refreshes every 2 s |

The nginx reverse-proxy (`lumina-frontend-main/nginx.conf`) proxies `/generate` to Node A (300 s timeout for CPU inference) and `/nodes/`, `/assignments/`, `/requests/` to the Tracker, so the frontend needs only one origin.

Configure:
- `VITE_API_BASE_URL` — points to Node A (port 8001)
- `VITE_TRACKER_BASE_URL` — points to the Tracker (port 8003)
