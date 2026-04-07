import torch
import requests
from fastapi import FastAPI, HTTPException
from transformers import AutoModelForCausalLM, AutoTokenizer

from lumina_sprint1.config import settings
from lumina_sprint1.schemas import GenerateRequest, GenerateResponse, TailForwardRequest
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Lumina Sprint1 Node A')


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = AutoModelForCausalLM.from_pretrained(settings.model_name).to(device).eval()
tokenizer = AutoTokenizer.from_pretrained(settings.model_name)


@torch.inference_mode()
def run_head(input_ids: torch.Tensor, attention_mask: torch.Tensor, split_layer: int) -> torch.Tensor:
    transformer = model.transformer
    hidden_states = transformer.wte(input_ids)

    if transformer.wpe is not None:
        position_ids = torch.arange(0, input_ids.shape[1], dtype=torch.long, device=input_ids.device)
        position_ids = position_ids.unsqueeze(0)
        hidden_states = hidden_states + transformer.wpe(position_ids)

    hidden_states = transformer.drop(hidden_states)

    for layer_idx in range(split_layer):
        block = transformer.h[layer_idx]
        block_outputs = block(hidden_states, attention_mask=None)
        hidden_states = block_outputs[0]

    return hidden_states


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'model': settings.model_name, 'split_layer': settings.split_layer}


@app.post('/generate', response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    encoded = tokenizer(request.prompt, return_tensors='pt')
    input_ids = encoded['input_ids'].to(device)
    attention_mask = encoded['attention_mask'].to(device)

    hidden_states = run_head(input_ids=input_ids, attention_mask=attention_mask, split_layer=settings.split_layer)

    payload = TailForwardRequest(
        token_ids_b64=tensor_to_b64(input_ids),
        attention_mask_b64=tensor_to_b64(attention_mask),
        hidden_states_b64=tensor_to_b64(hidden_states),
        split_layer=settings.split_layer,
        max_new_tokens=request.max_new_tokens,
    )

    try:
        response = requests.post(f"{settings.node_b_url}/forward_tail", json=payload.model_dump(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'Node B unavailable: {exc}') from exc

    body = response.json()
    next_token_ids = b64_to_tensor(body['generated_token_ids_b64'], device=device).long()
    merged = torch.cat([input_ids, next_token_ids], dim=1)

    generated_text = tokenizer.decode(merged[0], skip_special_tokens=True)
    return GenerateResponse(prompt=request.prompt, generated_text=generated_text)
