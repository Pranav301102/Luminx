import client from "./client";
import mockNodes from "../mocks/nodes.json";
import mockAssignments from "../mocks/assignments.json";

const USE_MOCKS = false;

export async function fetchNodes() {
  // TODO(Person 3): swap back to mocks if tracker is unreachable during development
  if (USE_MOCKS) {
    return mockNodes;
  }

  // Person 2: /nodes/list endpoint returns live node metadata and status
  // RESPONSE: { nodes: [{ node_id, role, vram, max_layers, status, latency_ms, throughput_tps, last_heartbeat }] }
  try {
    const response = await client.get("/nodes/list");
    return response.data;
  } catch (err) {
    console.warn("Failed to fetch live nodes, falling back to mocks:", err);
    return mockNodes;
  }
}

export async function fetchAssignments() {
  // TODO(Person 3): swap back to mocks if tracker is unreachable during development
  if (USE_MOCKS) {
    return mockAssignments;
  }

  // Person 2: /assignments/current endpoint returns active layer assignments
  // RESPONSE: { assignments: [{ node_id, layer_start, layer_end }] }
  try {
    const response = await client.get("/assignments/current");
    return response.data;
  } catch (err) {
    console.warn("Failed to fetch assignments, falling back to mocks:", err);
    return mockAssignments;
  }
}