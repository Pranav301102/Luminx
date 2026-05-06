import threading
import time

import torch
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lumina_sprint1.config import settings
from lumina_sprint1.model_adapter import load_model_for_node, make_layer_kwargs, run_all_layers, total_layer_count
from lumina_sprint1.schemas import (
    MidForwardRequest,
    MidForwardResponse,
    NodeHeartbeatRequest,
    NodeRegisterRequest,
    TailForwardRequest,
)
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Luminx Node B — Middle')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Model loading ─────────────────────────────────────────────────────────────
# Load only layers [split_layer_a, split_layer_b) assigned to this middle node.
model, device = load_model_for_node(
    settings.model_name,
    keep_start=settings.split_layer_a,
    keep_end=settings.split_layer_b,
)


def _estimate_vram_gb() -> float:
    if torch.cuda.is_available():
        return max(1.0, torch.cuda.get_device_properties(0).total_memory / (1024 ** 3))
    return 4.0


def _register_to_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeRegisterRequest(
        node_id=settings.node_b_id,
        role='mid',
        vram_gb=_estimate_vram_gb(),
        max_layers=settings.split_layer_b - settings.split_layer_a,
        total_layers=28,
    )
    try:
        requests.post(f'{settings.tracker_url}/register', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _heartbeat_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeHeartbeatRequest(node_id=settings.node_b_id)
    try:
        requests.post(f'{settings.tracker_url}/heartbeat', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


@torch.inference_mode()
def run_mid(hidden_states: torch.Tensor, seq_len: int) -> torch.Tensor:
    """Run all layers in the pruned middle model."""
    layer_kwargs = make_layer_kwargs(model, seq_len, device)
    return run_all_layers(model, hidden_states, layer_kwargs)


def _heartbeat_loop() -> None:
    while True:
        time.sleep(20)
        _heartbeat_tracker()


@app.on_event('startup')
def startup() -> None:
    _register_to_tracker()
    threading.Thread(target=_heartbeat_loop, daemon=True).start()


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'model': settings.model_name,
        'split_layer_a': settings.split_layer_a,
        'split_layer_b': settings.split_layer_b,
        'node_layers': total_layer_count(model),
    }


@app.post('/forward_mid', response_model=MidForwardResponse)
def forward_mid(request: MidForwardRequest) -> MidForwardResponse:
    """Receive hidden states from Node A, run middle layers, forward to Node C."""
    _heartbeat_tracker()

    token_ids = b64_to_tensor(request.token_ids_b64, device=device).long()
    hidden_states = b64_to_tensor(request.hidden_states_b64, device=device).to(device)
    seq_len = token_ids.shape[1]

    mid_output = run_mid(hidden_states, seq_len)

    # Forward to Node C
    tail_payload = TailForwardRequest(
        token_ids_b64=request.token_ids_b64,
        attention_mask_b64=request.attention_mask_b64,
        hidden_states_b64=tensor_to_b64(mid_output),
        max_new_tokens=request.max_new_tokens,
    )

    try:
        response = requests.post(
            f'{settings.node_c_url}/forward_tail',
            json=tail_payload.model_dump(),
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'Node C unavailable: {exc}') from exc

    body = response.json()
    return MidForwardResponse(generated_token_ids_b64=body['generated_token_ids_b64'])
