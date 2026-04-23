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


class NodeRegisterRequest(BaseModel):
    node_id: str = Field(..., min_length=1)
    role: str = Field(..., pattern='^(head|tail)$')
    vram_gb: float = Field(default=4.0, gt=0)
    max_layers: int = Field(..., ge=1)
    total_layers: int = Field(..., ge=2)


class NodeHeartbeatRequest(BaseModel):
    node_id: str = Field(..., min_length=1)


class NodeInfo(BaseModel):
    node_id: str
    role: str
    vram: float
    max_layers: int
    status: str
    latency_ms: float = 0.0
    throughput_tps: float = 0.0
    last_heartbeat: str


class NodeListResponse(BaseModel):
    nodes: list[NodeInfo] = []


class AssignmentEntry(BaseModel):
    node_id: str
    layer_start: int = Field(..., ge=0)
    layer_end: int = Field(..., ge=1)


class AssignmentsResponse(BaseModel):
    assignments: list[AssignmentEntry] = []


class AssignmentResponse(BaseModel):
    split_layer: int = Field(..., ge=1)
    total_layers: int = Field(..., ge=2)
    version: int = Field(..., ge=1)


class RequestStartRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    assigned_nodes: list[str] = Field(default_factory=list)


class RequestUpdateRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    status: str = Field(..., pattern='^(pending|in_progress|completed|failed)$')
    error: str = ''


class RequestTrace(BaseModel):
    request_id: str
    prompt: str
    status: str
    duration_ms: float
    assigned_nodes: list[str]
    error: str = ''


class RequestTraceResponse(BaseModel):
    trace: RequestTrace


class RequestTracesResponse(BaseModel):
    traces: list[RequestTrace] = []
