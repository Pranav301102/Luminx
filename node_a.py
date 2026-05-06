import torch
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer

from lumina_sprint1.config import settings
from lumina_sprint1.model_adapter import (
    get_initial_hidden_states,
    load_model_for_node,
    run_all_layers,
    total_layer_count,
)
from lumina_sprint1.schemas import (
    GenerateRequest,
    GenerateResponse,
    MidForwardRequest,
    NodeHeartbeatRequest,
    NodeRegisterRequest,
)
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Luminx Node A — Head')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Model loading ─────────────────────────────────────────────────────────────
# Load only layers [0, split_layer_a) to keep memory footprint small.
model, device = load_model_for_node(
    settings.model_name,
    keep_start=0,
    keep_end=settings.split_layer_a,
)
tokenizer = AutoTokenizer.from_pretrained(settings.model_name)
_full_layer_count = settings.split_layer_a  # pruned; we tell tracker the full count via registration


def _estimate_vram_gb() -> float:
    if torch.cuda.is_available():
        return max(1.0, torch.cuda.get_device_properties(0).total_memory / (1024 ** 3))
    return 4.0


def _register_to_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeRegisterRequest(
        node_id=settings.node_a_id,
        role='head',
        vram_gb=_estimate_vram_gb(),
        max_layers=settings.split_layer_a,
        total_layers=32,  # Phi-4 Mini total
    )
    try:
        requests.post(f'{settings.tracker_url}/register', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _heartbeat_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeHeartbeatRequest(node_id=settings.node_a_id)
    try:
        requests.post(f'{settings.tracker_url}/heartbeat', json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _resolve_split_layers() -> tuple[int, int]:
    """Fetch current split assignments from tracker."""
    fallback_a = settings.split_layer_a
    fallback_b = settings.split_layer_b
    if not settings.enable_dynamic_split:
        return fallback_a, fallback_b
    try:
        response = requests.get(f'{settings.tracker_url}/assignment', timeout=5)
        response.raise_for_status()
        data = response.json()
        split_a = int(data.get('split_layer_a', data.get('split_layer', fallback_a)))
        split_b = int(data.get('split_layer_b', fallback_b))
        return max(1, split_a), max(split_a + 1, split_b)
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return fallback_a, fallback_b


@torch.inference_mode()
def run_head(input_ids: torch.Tensor) -> torch.Tensor:
    """Embed input_ids and run all layers in the pruned head model."""
    hidden_states, layer_kwargs = get_initial_hidden_states(model, input_ids)
    return run_all_layers(model, hidden_states, layer_kwargs)


@app.on_event('startup')
def startup() -> None:
    _register_to_tracker()


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'model': settings.model_name,
        'split_layer_a': settings.split_layer_a,
        'split_layer_b': settings.split_layer_b,
        'dynamic_split_enabled': settings.enable_dynamic_split,
        'node_layers': total_layer_count(model),
    }


@app.post('/generate', response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    encoded = tokenizer(request.prompt, return_tensors='pt')
    current_ids = encoded['input_ids'].to(device)
    attention_mask = encoded['attention_mask'].to(device)

    _heartbeat_tracker()
    _resolve_split_layers()  # refreshes tracker knowledge; node uses its static range

    for _ in range(request.max_new_tokens):
        hidden_states = run_head(input_ids=current_ids)

        payload = MidForwardRequest(
            token_ids_b64=tensor_to_b64(current_ids),
            attention_mask_b64=tensor_to_b64(attention_mask),
            hidden_states_b64=tensor_to_b64(hidden_states),
            max_new_tokens=1,
        )

        try:
            response = requests.post(
                f'{settings.node_b_url}/forward_mid',
                json=payload.model_dump(),
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f'Node B unavailable: {exc}') from exc

        body = response.json()
        next_token_ids = b64_to_tensor(body['generated_token_ids_b64'], device=device).long()
        current_ids = torch.cat([current_ids, next_token_ids], dim=1)
        attention_mask = torch.ones_like(current_ids, device=device)

        eos = tokenizer.eos_token_id
        if eos is not None and int(next_token_ids[0, 0].item()) == eos:
            break

    generated_text = tokenizer.decode(current_ids[0], skip_special_tokens=True)
    return GenerateResponse(prompt=request.prompt, generated_text=generated_text)
