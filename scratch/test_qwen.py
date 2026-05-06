import torch
from transformers import AutoConfig, AutoModelForCausalLM

config = AutoConfig.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
with torch.device("meta"):
    model = AutoModelForCausalLM.from_config(config)

print("model_type:", config.model_type)
print("hasattr model.model.rotary_emb:", hasattr(model.model, "rotary_emb") if hasattr(model, "model") else "No model")
if hasattr(model, "model") and hasattr(model.model, "rotary_emb"):
    rotary_emb = model.model.rotary_emb
    print("rotary_emb:", rotary_emb)
    # Check inv_freq
    print("inv_freq:", getattr(rotary_emb, "inv_freq", None))
    # Let's try to call it
    try:
        x = torch.zeros(1, 10, 64)
        pos_ids = torch.arange(10).unsqueeze(0)
        res = rotary_emb(x, pos_ids)
        print("Success, returned type:", type(res))
        if isinstance(res, tuple):
            print("Tuple len:", len(res))
            for i, item in enumerate(res):
                print(f"  item {i}:", type(item), item.shape if hasattr(item, "shape") else item)
        else:
            print("Result:", res)
    except Exception as e:
        print("Failed direct call:", type(e), str(e))
