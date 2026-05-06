"""Architecture-agnostic helpers for split-inference layer access.

Supports:
- Phi3 / Phi-4 Mini (model.model.layers, model.model.embed_tokens)
- GPT-2 family    (model.transformer.h, model.transformer.wte)
"""
from __future__ import annotations

import gc

import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM


def _is_phi3_style(model: nn.Module) -> bool:
    return hasattr(model, 'model') and hasattr(model.model, 'embed_tokens')


def get_layers(model: nn.Module) -> nn.ModuleList:
    if _is_phi3_style(model):
        return model.model.layers
    if hasattr(model, 'transformer') and hasattr(model.transformer, 'h'):
        return model.transformer.h
    raise ValueError(f'Unsupported model architecture: {type(model).__name__}')


def get_final_norm(model: nn.Module) -> nn.Module:
    if _is_phi3_style(model):
        return model.model.norm
    if hasattr(model, 'transformer'):
        return model.transformer.ln_f
    raise ValueError(f'Unsupported model architecture: {type(model).__name__}')


def get_lm_head(model: nn.Module) -> nn.Module:
    return model.lm_head


def total_layer_count(model: nn.Module) -> int:
    return len(get_layers(model))


def get_initial_hidden_states(
    model: nn.Module,
    input_ids: torch.Tensor,
) -> tuple[torch.Tensor, dict]:
    """Embed input_ids and return (hidden_states, layer_kwargs).

    layer_kwargs holds the extra keyword args each layer's forward() needs.
    GPT-2 layers need nothing extra; Phi3 layers need position_ids + cache_position.
    """
    device = input_ids.device
    seq_len = input_ids.shape[1]

    if _is_phi3_style(model):
        hidden_states = model.model.embed_tokens(input_ids)
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        cache_position = torch.arange(seq_len, device=device)
        return hidden_states, {'position_ids': position_ids, 'cache_position': cache_position}

    # GPT-2 style
    transformer = model.transformer
    hidden_states = transformer.wte(input_ids)
    if transformer.wpe is not None:
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        hidden_states = hidden_states + transformer.wpe(position_ids)
    if hasattr(transformer, 'drop'):
        hidden_states = transformer.drop(hidden_states)
    return hidden_states, {}


def make_layer_kwargs(model: nn.Module, seq_len: int, device: torch.device) -> dict:
    """Build layer_kwargs for a node that receives hidden_states (not input_ids).

    Node B and Node C receive hidden_states from the previous node and must
    reconstruct position_ids for correct RoPE computation in Phi3 layers.
    """
    if _is_phi3_style(model):
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        cache_position = torch.arange(seq_len, device=device)
        return {'position_ids': position_ids, 'cache_position': cache_position}
    return {}


def run_all_layers(
    model: nn.Module,
    hidden_states: torch.Tensor,
    layer_kwargs: dict,
) -> torch.Tensor:
    """Run every layer currently in the model (after pruning)."""
    for layer in get_layers(model):
        outputs = layer(hidden_states, **layer_kwargs)
        hidden_states = outputs[0]
    return hidden_states


def get_logits(model: nn.Module, hidden_states: torch.Tensor) -> torch.Tensor:
    """Apply final norm + lm_head to get token logits."""
    hidden_states = get_final_norm(model)(hidden_states)
    return get_lm_head(model)(hidden_states)


def prune_to_range(model: nn.Module, keep_start: int, keep_end: int) -> None:
    """Remove all layers outside [keep_start, keep_end) to free memory.

    After this call get_layers(model) contains only the kept layers,
    re-indexed from 0. run_all_layers() will execute only those layers.
    """
    layers = get_layers(model)
    n = len(layers)
    keep_start = max(0, keep_start)
    keep_end = min(n, keep_end)

    if keep_start == 0 and keep_end == n:
        return

    kept = [layers[i] for i in range(keep_start, keep_end)]

    layers._modules.clear()
    for idx, layer in enumerate(kept):
        layers._modules[str(idx)] = layer

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()


def load_model_for_node(model_name: str, keep_start: int, keep_end: int):
    """Load model with appropriate precision and prune to assigned layer range.

    On CUDA machines: uses int8 quantization via bitsandbytes when available,
    otherwise fp16. On CPU machines: uses fp16 with low_cpu_mem_usage.

    Returns (model, device).
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    if torch.cuda.is_available():
        try:
            import bitsandbytes  # noqa: F401
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                load_in_8bit=True,
                device_map='auto',
            )
        except (ImportError, RuntimeError):
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map='auto',
            )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )

    model.eval()
    prune_to_range(model, keep_start, keep_end)
    return model, device
