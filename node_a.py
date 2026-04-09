import torch
import requests
from fastapi import FastAPI, HTTPException
from transformers import AutoModelForCausalLM, AutoTokenizer

from lumina_sprint1.config import settings
from lumina_sprint1.schemas import (
    GenerateRequest,
    GenerateResponse,
    NodeHeartbeatRequest,
    NodeRegisterRequest,
    TailForwardRequest,
)
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Lumina Sprint1 Node A')


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = AutoModelForCausalLM.from_pretrained(settings.model_name).to(device).eval()
tokenizer = AutoTokenizer.from_pretrained(settings.model_name)
total_layers = len(model.transformer.h)


def _estimate_vram_gb() -> float:
    if torch.cuda.is_available():
        return max(1.0, torch.cuda.get_device_properties(0).total_memory / (1024**3))
    return 4.0


def _register_to_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeRegisterRequest(
        node_id=settings.node_a_id,
        role='head',
        vram_gb=_estimate_vram_gb(),
        max_layers=max(1, total_layers - 1),
        total_layers=total_layers,
    )
    try:
        requests.post(f"{settings.tracker_url}/register", json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _heartbeat_tracker() -> None:
    if not settings.enable_dynamic_split:
        return
    payload = NodeHeartbeatRequest(node_id=settings.node_a_id)
    try:
        requests.post(f"{settings.tracker_url}/heartbeat", json=payload.model_dump(), timeout=5)
    except requests.RequestException:
        pass


def _resolve_split_layer() -> int:
    fallback = max(1, min(settings.split_layer, total_layers - 1))
    if not settings.enable_dynamic_split:
        return fallback
    try:
        response = requests.get(f"{settings.tracker_url}/assignment", timeout=5)
        response.raise_for_status()
        split_layer = int(response.json()['split_layer'])
        return max(1, min(split_layer, total_layers - 1))
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return fallback


@torch.inference_mode()
def run_head(input_ids: torch.Tensor, attention_mask: torch.Tensor, split_layer: int) -> torch.Tensor:
    transformer = model.transformer
    hidden_states = transformer.wte(input_ids)

    if transformer.wpe is not None:
        position_ids = torch.arange(0, input_ids.shape[1], dtype=torch.long, device=input_ids.device)
        position_ids = position_ids.unsqueeze(0)
        hidden_states = hidden_states + transformer.wpe(position_ids)

    hidden_states = transformer.drop(hidden_states)

    split_layer = max(1, min(split_layer, len(transformer.h) - 1))
    for layer_idx in range(split_layer):
        block = transformer.h[layer_idx]
        block_outputs = block(hidden_states, attention_mask=None)
        hidden_states = block_outputs[0]

    return hidden_states


@app.on_event('startup')
def startup() -> None:
    _register_to_tracker()


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'model': settings.model_name,
        'split_layer': settings.split_layer,
        'dynamic_split_enabled': settings.enable_dynamic_split,
        'total_layers': total_layers,
    }


@app.post('/generate', response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    encoded = tokenizer(request.prompt, return_tensors='pt')
    current_ids = encoded['input_ids'].to(device)
    attention_mask = encoded['attention_mask'].to(device)

    _heartbeat_tracker()

    for _ in range(request.max_new_tokens):
        split_layer = _resolve_split_layer()
        hidden_states = run_head(input_ids=current_ids, attention_mask=attention_mask, split_layer=split_layer)

        payload = TailForwardRequest(
            token_ids_b64=tensor_to_b64(current_ids),
            attention_mask_b64=tensor_to_b64(attention_mask),
            hidden_states_b64=tensor_to_b64(hidden_states),
            split_layer=split_layer,
            max_new_tokens=1,
        )

        try:
            response = requests.post(f"{settings.node_b_url}/forward_tail", json=payload.model_dump(), timeout=30)
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
