from fastapi import FastAPI, HTTPException

from lumina_sprint1.config import settings
from lumina_sprint1.schemas import (
    AssignmentEntry,
    AssignmentResponse,
    AssignmentsResponse,
    NodeHeartbeatRequest,
    NodeListResponse,
    NodeRegisterRequest,
    RequestStartRequest,
    RequestTraceResponse,
    RequestTracesResponse,
    RequestTrace,
    RequestUpdateRequest,
)
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


@app.get('/nodes/list', response_model=NodeListResponse)
def list_nodes() -> NodeListResponse:
    return NodeListResponse(nodes=manager.node_list())


@app.get('/assignments/current', response_model=AssignmentsResponse)
def get_current_assignments() -> AssignmentsResponse:
    return AssignmentsResponse(assignments=manager.node_assignments())


@app.post('/lease/renew', response_model=AssignmentResponse)
def lease_renewal(request: NodeHeartbeatRequest) -> AssignmentResponse:
    if request.node_id not in manager.nodes:
        raise HTTPException(status_code=404, detail=f'Unknown node_id: {request.node_id}')

    manager.lease_renewal(request.node_id)
    split, total, version = manager.assignment()
    return AssignmentResponse(split_layer=split, total_layers=total, version=version)


@app.post('/requests/start', response_model=dict)
def start_request(request: RequestStartRequest) -> dict:
    manager.start_request(request.request_id, request.prompt, request.assigned_nodes)
    return {'request_id': request.request_id, 'status': 'started'}


@app.post('/requests/update', response_model=dict)
def update_request(request: RequestUpdateRequest) -> dict:
    manager.update_request(request.request_id, request.status, request.error)
    return {'request_id': request.request_id, 'status': request.status}


@app.get('/requests/trace/{request_id}', response_model=RequestTraceResponse)
def get_request_trace(request_id: str) -> RequestTraceResponse:
    trace = manager.get_request_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f'Request not found: {request_id}')
    return RequestTraceResponse(trace=RequestTrace(**trace))


@app.get('/requests/traces', response_model=RequestTracesResponse)
def get_request_traces(limit: int = 100) -> RequestTracesResponse:
    traces_data = manager.list_request_traces(limit)
    return RequestTracesResponse(traces=[RequestTrace(**t) for t in traces_data])
