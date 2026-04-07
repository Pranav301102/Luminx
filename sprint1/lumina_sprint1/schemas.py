from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_new_tokens: int = Field(default=20, ge=1, le=128)


class GenerateResponse(BaseModel):
    prompt: str
    generated_text: str


class TailForwardRequest(BaseModel):
    token_ids_b64: str
    attention_mask_b64: str
    hidden_states_b64: str
    split_layer: int = Field(..., ge=0)
    max_new_tokens: int = Field(default=20, ge=1, le=128)


class TailForwardResponse(BaseModel):
    generated_token_ids_b64: str
