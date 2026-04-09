import pytest

torch = pytest.importorskip('torch')

from lumina_sprint1.tensor_codec import b64_to_tensor, tensor_to_b64


def test_tensor_codec_roundtrip() -> None:
    original = torch.randn(2, 3, 4, dtype=torch.float32)
    encoded = tensor_to_b64(original)
    decoded = b64_to_tensor(encoded, device=torch.device('cpu'))

    assert decoded.shape == original.shape
    assert decoded.dtype == original.dtype
    assert torch.allclose(decoded, original)
