from fastapi import FastAPI, HTTPException

from lumina_sprint1.config import settings
from lumina_sprint1.schemas import AssignmentResponse, NodeHeartbeatRequest, NodeRegisterRequest
from lumina_sprint1.tracker_core import AssignmentManager

app = FastAPI(title='Lumina Sprint1 Tracker')

manager = AssignmentManager(
    total_layers=4,
    fallback_split_layer=settings.split_layer,
    heartbeat_timeout_sec=settings.heartbeat_timeout_sec,
)


@app.post('/register', response_model=AssignmentResponse)
def register(request: NodeRegisterRequest) -> AssignmentResponse:
    split_layer = manager.upsert_node(
        node_id=request.node_id,
        role=request.role,
        vram_gb=request.vram_gb,
        max_layers=request.max_layers,
        total_layers=request.total_layers,
    )
    split, total, version = manager.assignment()
    return AssignmentResponse(split_layer=split_layer or split, total_layers=total, version=version)


@app.post('/heartbeat', response_model=AssignmentResponse)
def heartbeat(request: NodeHeartbeatRequest) -> AssignmentResponse:
    if request.node_id not in manager.nodes:
        raise HTTPException(status_code=404, detail=f'Unknown node_id: {request.node_id}')
    manager.heartbeat(request.node_id)
    split, total, version = manager.assignment()
    return AssignmentResponse(split_layer=split, total_layers=total, version=version)


@app.get('/assignment', response_model=AssignmentResponse)
def get_assignment() -> AssignmentResponse:
    split, total, version = manager.assignment()
    return AssignmentResponse(split_layer=split, total_layers=total, version=version)
