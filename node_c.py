import torch
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumina_sprint1.config import settings
from lumina_sprint1.model_adapter import (
    get_logits,
    load_model_for_node,
    make_layer_kwargs,
    run_all_layers,
    total_layer_count,
)
from lumina_sprint1.schemas import (
    NodeHeartbeatRequest,
    NodeRegisterRequest,
    TailForwardRequest,
    TailForwardResponse,
)
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Luminx Node C — Tail')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Model loading ─────────────────────────────────────────────────────────────
# Load only layers [split_layer_b, total) plus final norm + lm_head.
# total_layers=32 for Phi-4 Mini.
model, device = load_model_for_node(
    settings.model_name,
    keep_start=settings.split_layer_b,
    keep_end=32,
)


def _estimate_vram_gb() -> float:
    if torch.cuda.is_available():
        return max(1.0, torch.cuda.get_device_properties(0).total_memory / (1024 ** 3))
    return 4.0


def _register_to_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeRegisterRequest(
        node_id=settings.node_c_id,
        role='tail',
        vram_gb=_estimate_vram_gb(),
        max_layers=32 - settings.split_layer_b,
        total_layers=32,
    )
    try:
        requests.post(f'{settings.tracker_url}/register', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _heartbeat_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeHeartbeatRequest(node_id=settings.node_c_id)
    try:
        requests.post(f'{settings.tracker_url}/heartbeat', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


@torch.inference_mode()
def run_tail(hidden_states: torch.Tensor, seq_len: int) -> torch.Tensor:
    """Run final layers, apply norm + lm_head, return next token id."""
    layer_kwargs = make_layer_kwargs(model, seq_len, device)
    hidden_states = run_all_layers(model, hidden_states, layer_kwargs)
    logits = get_logits(model, hidden_states)
    next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
    return next_token


@app.on_event('startup')
def startup() -> None:
    _register_to_tracker()


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'model': settings.model_name,
        'split_layer_b': settings.split_layer_b,
        'node_layers': total_layer_count(model),
    }


@app.post('/forward_tail', response_model=TailForwardResponse)
def forward_tail(request: TailForwardRequest) -> TailForwardResponse:
    """Receive hidden states from Node B, run final layers, return next token."""
    _heartbeat_tracker()

    token_ids = b64_to_tensor(request.token_ids_b64, device=device).long()
    hidden_states = b64_to_tensor(request.hidden_states_b64, device=device).to(device)
    seq_len = token_ids.shape[1]

    next_token = run_tail(hidden_states, seq_len)
    return TailForwardResponse(generated_token_ids_b64=tensor_to_b64(next_token))
