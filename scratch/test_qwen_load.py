import torch
import traceback
from lumina_sprint1.model_adapter import load_model_for_node, make_layer_kwargs, run_all_layers

print("Loading model slice [9, 19) for Qwen2.5-1.5B-Instruct...")
try:
    model, device = load_model_for_node(
        "Qwen/Qwen2.5-1.5B-Instruct",
        keep_start=9,
        keep_end=19
    )
    print("Model loaded successfully!")
    print("Device:", device)
    
    # Try to make layer kwargs and run layers
    seq_len = 10
    hidden_states = torch.randn(1, seq_len, 1536, device=device)
    
    print("Building layer kwargs...")
    layer_kwargs = make_layer_kwargs(model, seq_len, device)
    print("layer_kwargs keys:", list(layer_kwargs.keys()))
    if "position_embeddings" in layer_kwargs:
        pe = layer_kwargs["position_embeddings"]
        print("position_embeddings type:", type(pe))
        if isinstance(pe, tuple):
            print("position_embeddings len:", len(pe))
            for i, item in enumerate(pe):
                print(f"  item {i}:", type(item), item.shape if hasattr(item, "shape") else item)
        else:
            print("position_embeddings val:", pe)
            
    print("Running layers...")
    out = run_all_layers(model, hidden_states, layer_kwargs)
    print("Success! Output shape:", out.shape)

except Exception as e:
    print("An error occurred:")
    traceback.print_exc()
