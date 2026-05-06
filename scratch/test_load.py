import torch
from transformers import AutoConfig, AutoModelForCausalLM
import gc

model_name = "sshleifer/tiny-gpt2"
config = AutoConfig.from_pretrained(model_name)

# Assume 2 layers, we only want layer 0
device_map = {
    "transformer.wte": "cpu",
    "transformer.wpe": "cpu",
    "transformer.drop": "cpu",
    "transformer.h.0": "cpu",
    "transformer.h.1": "meta", # put unused on meta!
    "transformer.ln_f": "cpu",
    "lm_head": "cpu"
}

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map=device_map,
    torch_dtype=torch.float16
)

print(model.transformer.h[0].weight.device)
# If transformer.h.1 is on meta, this worked!
print(model.transformer.h[1].weight.device)

