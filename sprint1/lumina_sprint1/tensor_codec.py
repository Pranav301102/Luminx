import base64
from io import BytesIO

import torch


def tensor_to_b64(tensor: torch.Tensor) -> str:
    buffer = BytesIO()
    torch.save(tensor.detach().cpu(), buffer)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def b64_to_tensor(value: str, device: torch.device) -> torch.Tensor:
    data = base64.b64decode(value.encode('utf-8'))
    buffer = BytesIO(data)
    tensor = torch.load(buffer, map_location=device)
    return tensor
