from fastapi import FastAPI
import torch
from transformers import AutoModelForCausalLM

from lumina_sprint1.config import settings
from lumina_sprint1.schemas import TailForwardRequest, TailForwardResponse
from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64

app = FastAPI(title='Lumina Sprint1 Node B')


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = AutoModelForCausalLM.from_pretrained(settings.model_name).to(device).eval()


@torch.inference_mode()
def run_tail(
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    hidden_states: torch.Tensor,
    split_layer: int,
    max_new_tokens: int,
) -> torch.Tensor:
    transformer = model.transformer
    blocks = transformer.h

    outputs = hidden_states
    for layer_idx in range(split_layer, len(blocks)):
        block = blocks[layer_idx]
        block_outputs = block(outputs, attention_mask=None)
        outputs = block_outputs[0]

    outputs = transformer.ln_f(outputs)
    logits = model.lm_head(outputs)

    # PoC mode: return one next token using the last position logits.
    next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
    return next_token


@app.post('/forward_tail', response_model=TailForwardResponse)
def forward_tail(request: TailForwardRequest) -> TailForwardResponse:
    token_ids = b64_to_tensor(request.token_ids_b64, device=device).long()
    attention_mask = b64_to_tensor(request.attention_mask_b64, device=device).long()
    hidden_states = b64_to_tensor(request.hidden_states_b64, device=device).to(device)

    generated_ids = run_tail(
        input_ids=token_ids,
        attention_mask=attention_mask,
        hidden_states=hidden_states,
        split_layer=request.split_layer,
        max_new_tokens=request.max_new_tokens,
    )

    return TailForwardResponse(generated_token_ids_b64=tensor_to_b64(generated_ids))
