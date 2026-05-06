# Lumina — Distributed Split Inference

Lumina runs a language model across two machines by splitting the transformer layers between them. Rather than having one machine handle the entire model, a Tracker dynamically decides how many layers each node should run based on its available VRAM.

## How It Works

```
Client
  │
  ▼ POST /generate
┌─────────────────────────────┐
│  Node A  (port 8001)        │  ← Head layers (0 → split_layer)
│  Tokenizes prompt           │
│  Runs first N blocks        │
│  Serializes hidden states   │
└──────────────┬──────────────┘
               │ POST /forward_tail (base64 tensor)
               ▼
┌─────────────────────────────┐
│  Node B  (port 8002)        │  ← Tail layers (split_layer → end)
│  Runs remaining blocks      │
│  Applies ln_f + lm_head     │
│  Returns next token         │
└─────────────────────────────┘

Both nodes register/heartbeat with:

┌─────────────────────────────┐
│  Tracker  (port 8003)       │
│  Monitors node health       │
│  Computes optimal split     │
│  Exposes /assignment        │
└─────────────────────────────┘
```

The split point is recalculated on every heartbeat proportional to each node's VRAM:
```
split_layer = round((node_a_vram / total_vram) * total_layers)
```

## Project Layout

```
lumina_sprint1/
├── config.py          # pydantic-settings config (env vars / .env)
├── schemas.py         # shared Pydantic request/response models
├── tensor_codec.py    # tensor ↔ base64 serialization
└── tracker_core.py    # AssignmentManager — split logic + request traces

node_a.py              # Head node — /generate endpoint
node_b.py              # Tail node — /forward_tail endpoint
tracker.py             # Tracker service
docker-compose.yml     # Single-machine local dev (all 3 services)
docker-compose.head.yml  # Head instance (Node A + Tracker)
docker-compose.tail.yml  # Tail instance (Node B only)
docker/Dockerfile      # Single image used by all services
deploy-ec2/            # EC2 deployment (dev/demo)
terraform/             # AWS Fargate deployment (production)
lumina-frontend-main/  # React dashboard
```

## Prerequisites

- Python 3.11+
- Docker + Docker Compose

## Local Run (single machine)

```bash
pip install -r requirements.txt
docker compose up --build
```

Test it:
```bash
curl -X POST http://localhost:8001/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Lumina is", "max_new_tokens": 20}'
```

Run tests:
```bash
pytest -q
```

## Configuration

All settings are read from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `sshleifer/tiny-gpt2` | HuggingFace model |
| `SPLIT_LAYER` | `2` | Fallback split layer index |
| `NODE_B_URL` | `http://localhost:8002` | Node B address (used by Node A) |
| `TRACKER_URL` | `http://localhost:8003` | Tracker address |
| `ENABLE_DYNAMIC_SPLIT` | `true` | Let tracker override split layer |
| `NODE_A_ID` / `NODE_B_ID` | `node-a` / `node-b` | Node identifiers |
| `HEARTBEAT_TIMEOUT_SEC` | `30` | Seconds before a node is marked stale |

## API Reference

### Node A
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Node status, model, split layer |
| `POST` | `/generate` | Generate text — `{"prompt": "...", "max_new_tokens": 20}` |

### Node B
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Node status, model, total layers |
| `POST` | `/forward_tail` | Run tail layers on received hidden states |

### Tracker
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/assignment` | Current split layer + version |
| `GET` | `/nodes/list` | All registered nodes and their status |
| `GET` | `/assignments/current` | Layer ranges assigned per node |
| `POST` | `/register` | Register a node with VRAM + layer capacity |
| `POST` | `/heartbeat` | Refresh a node's last-seen timestamp |
| `GET` | `/requests/traces` | Recent request history with timing |

## Deployment

### Option 1 — Dev/Demo on EC2 (3 instances, ~$10–30/month)

Deploys the true split inference architecture: Node A + Tracker on one machine, Node B on a second, frontend on a third.

**Prerequisites:** AWS CLI configured, Terraform ≥ 1.5, an EC2 key pair.

```bash
cd deploy-ec2

# 1. Create the 3 EC2 instances
terraform init
terraform apply \
  -var="key_pair_name=<your-key-pair-name>" \
  -var="your_ip_cidr=$(curl -s https://checkip.amazonaws.com)/32"

# 2. Wait ~90 seconds for instances to boot, then deploy
./deploy.sh ~/.ssh/<your-key-pair-name>.pem
```

The deploy script will output:
```
Frontend  : http://<frontend-ip>
Generate  : http://<head-ip>:8001/generate
Tracker   : http://<head-ip>:8003/assignment
```

**Tear down:**
```bash
terraform destroy \
  -var="key_pair_name=<your-key-pair-name>" \
  -var="your_ip_cidr=$(curl -s https://checkip.amazonaws.com)/32"
```

**Instance breakdown:**

| Instance | Type | Services |
|----------|------|----------|
| `luminx-head` | t3.small | Node A (port 8001) + Tracker (port 8003) |
| `luminx-tail` | t3.small | Node B (port 8002) |
| `luminx-frontend` | t3.micro | nginx + React frontend (port 80) |

### Option 2 — Production on AWS Fargate

Full production setup with VPC, ECS Fargate, ALB, ECR, and CloudWatch. See `terraform/` for details.

```bash
cd terraform
terraform init
terraform apply
```

> Requires an S3 bucket + DynamoDB table for remote state — uncomment the backend block in `terraform/main.tf` first.

**Cost:** ~$75–90/month running 24/7.

## Architecture: 3-Instance Split

```
Instance 1 — luminx-head
  ├── Node A  :8001  (GPT-2 layers 0 → split_layer)
  └── Tracker :8003  (dynamic split assignment)
          │
          │ hidden states over HTTP
          ▼
Instance 2 — luminx-tail
  └── Node B  :8002  (GPT-2 layers split_layer → 12)

Instance 3 — luminx-frontend
  └── nginx   :80   (React dashboard)
```

## Model Notes

- Default: `sshleifer/tiny-gpt2` — 2 layers, ~50MB. Pipeline validation only, output is not meaningful.
- Recommended for demos: `gpt2` — 12 layers, ~500MB, coherent English output.
- Change via `MODEL_NAME` env var in `docker-compose.head.yml` and `docker-compose.tail.yml`.

## Frontend

React dashboard with four pages:

| Page | Description |
|------|-------------|
| Chat | Type a prompt and generate text via the live API |
| Health | Node A/B status, model name, layer count |
| Cluster | Live node list — role, VRAM, status, last heartbeat |
| Trace | Request history with duration and assigned nodes |

Built with Vite + React. Configure `VITE_API_BASE_URL` to point to the head instance.
