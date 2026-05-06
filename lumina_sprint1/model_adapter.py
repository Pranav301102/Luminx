"""Architecture-agnostic helpers for split-inference layer access.

Supports:
- Phi3 / Phi-4 Mini (model.model.layers, model.model.embed_tokens)
- GPT-2 family    (model.transformer.h, model.transformer.wte)
"""
from __future__ import annotations

import gc
import json

import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModelForCausalLM


def _model_type(model: nn.Module) -> str:
    config = getattr(model, 'config', None)
    return str(getattr(config, 'model_type', '')).lower()


def _is_phi3_style(model: nn.Module) -> bool:
    model_type = _model_type(model)
    if model_type:
        return model_type.startswith('phi3') or model_type.startswith('phi4') or model_type == 'phi'
    return hasattr(model, 'model') and hasattr(model.model, 'embed_tokens')


def _is_qwen2_style(model: nn.Module) -> bool:
    return _model_type(model) in {'qwen2', 'qwen2_moe'}


def _has_model_layers(model: nn.Module) -> bool:
    return hasattr(model, 'model') and hasattr(model.model, 'layers')


def get_layers(model: nn.Module) -> nn.ModuleList:
    if _has_model_layers(model):
        return model.model.layers
    if hasattr(model, 'transformer') and hasattr(model.transformer, 'h'):
        return model.transformer.h
    raise ValueError(f'Unsupported model architecture: {type(model).__name__}')


def get_final_norm(model: nn.Module) -> nn.Module:
    if hasattr(model, 'model') and hasattr(model.model, 'norm'):
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
    """Embed input_ids and return (hidden_states, layer_kwargs)."""
    device = input_ids.device
    seq_len = input_ids.shape[1]

    if _is_phi3_style(model):
        hidden_states = model.model.embed_tokens(input_ids)
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        cache_position = torch.arange(seq_len, device=device)
        return hidden_states, {'position_ids': position_ids, 'cache_position': cache_position}

    if _is_qwen2_style(model):
        hidden_states = model.model.embed_tokens(input_ids)
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        position_embeddings = _get_qwen2_position_embeddings(
            model,
            hidden_states=hidden_states,
            position_ids=position_ids,
            device=device,
        )
        return hidden_states, {
            'position_embeddings': position_embeddings,
            'position_ids': position_ids,
        }

    transformer = model.transformer
    hidden_states = transformer.wte(input_ids)
    if transformer.wpe is not None:
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        hidden_states = hidden_states + transformer.wpe(position_ids)
    if hasattr(transformer, 'drop'):
        hidden_states = transformer.drop(hidden_states)
    return hidden_states, {}


def make_layer_kwargs(model: nn.Module, seq_len: int, device: torch.device) -> dict:
    """Build layer_kwargs for mid/tail nodes that receive hidden_states."""
    if _is_phi3_style(model):
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        cache_position = torch.arange(seq_len, device=device)
        return {'position_ids': position_ids, 'cache_position': cache_position}
    if _is_qwen2_style(model):
        position_ids = torch.arange(seq_len, dtype=torch.long, device=device).unsqueeze(0)
        position_embeddings = _get_qwen2_position_embeddings(
            model,
            hidden_states=None,
            position_ids=position_ids,
            device=device,
        )
        return {
            'position_embeddings': position_embeddings,
            'position_ids': position_ids,
        }
    return {}


def run_all_layers(
    model: nn.Module,
    hidden_states: torch.Tensor,
    layer_kwargs: dict,
) -> torch.Tensor:
    """Run every layer currently in the model (after pruning)."""
    for layer in get_layers(model):
        outputs = layer(hidden_states, **layer_kwargs)
        if isinstance(outputs, (tuple, list)):
            hidden_states = outputs[0]
        else:
            hidden_states = outputs
    return hidden_states


def get_logits(model: nn.Module, hidden_states: torch.Tensor) -> torch.Tensor:
    """Apply final norm + lm_head to get token logits."""
    hidden_states = get_final_norm(model)(hidden_states)
    return get_lm_head(model)(hidden_states)


def prune_to_range(model: nn.Module, keep_start: int, keep_end: int) -> None:
    """Remove all layers outside [keep_start, keep_end) in-place."""
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


def _layer_prefix(config) -> str | None:
    if hasattr(config, 'num_hidden_layers'):
        return 'model.layers'
    if hasattr(config, 'n_layer'):
        return 'transformer.h'
    return None


def _load_slice_cpu(model_name: str, keep_start: int, keep_end: int) -> nn.Module:
    """Load only the assigned layer slice into CPU RAM using safetensors directly.

    Strategy:
      1. Create the full model skeleton on the 'meta' device — zero RAM.
      2. Read only the tensors for [keep_start, keep_end) plus always-needed
         weights (embeddings, norm, lm_head) from the safetensors shards.
      3. Assign those tensors into the model with load_state_dict(assign=True).

    No accelerate required; no hooks attached.
    """
    from safetensors import safe_open
    from huggingface_hub import hf_hub_download

    config = AutoConfig.from_pretrained(model_name)
    prefix = _layer_prefix(config)

    # Build model skeleton entirely on meta (no real memory allocated)
    with torch.device('meta'):
        model = AutoModelForCausalLM.from_config(config, torch_dtype=torch.float32)

    total_layer_count_cfg = getattr(config, 'num_hidden_layers', None) or getattr(config, 'n_layer', 0)
    is_head = keep_start == 0
    is_tail = keep_end >= total_layer_count_cfg

    def _is_needed(param_name: str) -> bool:
        # Layer slice: only load the assigned range
        if prefix is not None and param_name.startswith(prefix + '.'):
            rest = param_name[len(prefix) + 1:]
            try:
                layer_idx = int(rest.split('.')[0])
                return keep_start <= layer_idx < keep_end
            except (ValueError, IndexError):
                return True

        # Embedding table: only the head node needs it
        if 'embed_tokens' in param_name:
            return is_head

        # LM head: only the tail node needs it
        if param_name.startswith('lm_head.'):
            return is_tail

        # Final norm (e.g. model.norm.weight, model.model.norm.weight): tail only
        # These are short paths — layer-internal norms are already covered above
        if 'norm' in param_name and (prefix is None or not param_name.startswith(prefix + '.')):
            return is_tail

        return True

    # Find which shards contain our needed parameters
    try:
        index_path = hf_hub_download(model_name, 'model.safetensors.index.json')
        with open(index_path) as f:
            weight_map: dict = json.load(f)['weight_map']
        needed_shards = sorted({v for k, v in weight_map.items() if _is_needed(k)})
    except Exception:
        # Single-file model (no index)
        needed_shards = ['model.safetensors']
        weight_map = {}

    # Load only the needed tensors from each shard
    state_dict: dict[str, torch.Tensor] = {}
    for shard_filename in needed_shards:
        local_path = hf_hub_download(model_name, shard_filename)
        with safe_open(local_path, framework='pt', device='cpu') as f:
            for key in f.keys():
                if _is_needed(key):
                    state_dict[key] = f.get_tensor(key).to(torch.float32)

    # assign=True replaces meta tensors with real CPU tensors in-place
    model.load_state_dict(state_dict, strict=False, assign=True)
    _ensure_qwen2_rotary_buffers(model)
    return model


def load_model_for_node(model_name: str, keep_start: int, keep_end: int):
    """Load only the assigned layer range into memory. No accelerate needed.

    CPU path: uses safetensors direct loading — only the needed layer slice
    is ever materialised in RAM (~2-3 GB instead of the full 7+ GB).

    Returns (model, device).
    """
    device_name = 'cuda' if torch.cuda.is_available() else 'cpu'
    device = torch.device(device_name)

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
        model = _load_slice_cpu(model_name, keep_start, keep_end)

    _ensure_qwen2_rotary_buffers(model)
    model.eval()
    prune_to_range(model, keep_start, keep_end)
    return model, device


def _get_qwen2_rotary_emb(model: nn.Module) -> nn.Module | None:
    if hasattr(model, 'model') and hasattr(model.model, 'rotary_emb'):
        return model.model.rotary_emb
    layers = get_layers(model)
    if layers and hasattr(layers[0], 'self_attn') and hasattr(layers[0].self_attn, 'rotary_emb'):
        return layers[0].self_attn.rotary_emb
    return None


def _ensure_qwen2_rotary_buffers(model: nn.Module) -> None:
    if not _is_qwen2_style(model):
        return
    rotary_emb = _get_qwen2_rotary_emb(model)
    if rotary_emb is None:
        return
    inv_freq = getattr(rotary_emb, 'inv_freq', None)
    if isinstance(inv_freq, torch.Tensor) and inv_freq.is_meta:
        dim = getattr(rotary_emb, 'dim', None)
        if dim is None:
            head_dim = getattr(model.config, 'hidden_size', 0) // max(1, getattr(model.config, 'num_attention_heads', 1))
            dim = head_dim
        base = getattr(rotary_emb, 'base', None)
        if base is None:
            base = getattr(model.config, 'rope_theta', 10000)
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim))
        if hasattr(rotary_emb, '_buffers') and 'inv_freq' in rotary_emb._buffers:
            rotary_emb._buffers['inv_freq'] = inv_freq
        else:
            rotary_emb.register_buffer('inv_freq', inv_freq, persistent=False)


def _get_qwen2_position_embeddings(
    model: nn.Module,
    hidden_states: torch.Tensor | None,
    position_ids: torch.Tensor,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    rotary_emb = _get_qwen2_rotary_emb(model)
    if rotary_emb is None:
        raise ValueError('Qwen2 rotary embedding module not found.')

    if hidden_states is None:
        param = next(model.parameters(), None)
        dtype = param.dtype if param is not None else torch.float32
        dim = getattr(rotary_emb, 'dim', None)
        if dim is None:
            head_dim = getattr(model.config, 'hidden_size', 0) // max(1, getattr(model.config, 'num_attention_heads', 1))
            dim = head_dim
        hidden_states = torch.zeros(1, position_ids.shape[1], dim, device=device, dtype=dtype)

    try:
        return rotary_emb(hidden_states, position_ids)
    except TypeError:
        try:
            return rotary_emb(hidden_states, position_ids=position_ids)
        except TypeError:
            return rotary_emb(hidden_states, seq_len=position_ids.shape[1])
