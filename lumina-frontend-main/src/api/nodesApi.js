import axios from "axios";
import mockNodes from "../mocks/nodes.json";
import mockAssignments from "../mocks/assignments.json";

// Toggle between real backend APIs and local mock data
// true  -> use local mock JSON files
// false -> use live backend APIs
const USE_MOCKS = false;

const trackerClient = axios.create({
  baseURL: import.meta.env.VITE_TRACKER_BASE_URL || "",
  timeout: 10000,
});

/**
 * Fetch all available compute nodes from the backend tracker service.
 * 
 * Backend response format:
 * {
 *   nodes: [
 *     {
 *       node_id,
 *       role,
 *       vram,
 *       max_layers,
 *       status,
 *       cpu_percent,
 *       ram_percent,
 *       ram_used_gb,
 *       ram_total_gb,
 *       latency_ms,
 *       throughput_tps,
 *       active_connections,
 *       shared_with,
 *       last_heartbeat
 *     }
 *   ]
 * }
 */
export async function fetchNodes() {
  // Person 3:
  // During frontend development, enable mocks if the backend
  // tracker service is offline or not ready yet.
  if (USE_MOCKS) {
    return mockNodes;
  }

  // Person 2:
  // Live backend endpoint that returns current node information
  // and health status from the distributed system tracker.
  try {
    const response = await trackerClient.get("/nodes/list");

    // Return backend JSON response data
    return response.data;
  } catch (err) {
    // If API fails, automatically fallback to mock data
    // so frontend development can continue without backend dependency
    console.warn(
      "Failed to fetch live nodes, falling back to mocks:",
      err
    );

    return mockNodes;
  }
}

/**
 * Fetch current model layer assignments for all active nodes.
 * 
 * Backend response format:
 * {
 *   assignments: [
 *     {
 *       node_id,
 *       layer_start,
 *       layer_end
 *     }
 *   ]
 * }
 */
export async function fetchAssignments() {
  // Person 3:
  // Use local mock assignments if backend tracker
  // service is unavailable during development.
  if (USE_MOCKS) {
    return mockAssignments;
  }

  // Person 2:
  // Live backend endpoint that returns active
  // distributed layer allocation information.
  try {
    const response = await trackerClient.get("/assignments/current");

    // Return assignment data from backend
    return response.data;
  } catch (err) {
    // Fallback to local mock assignment data
    // if backend request fails
    console.warn(
      "Failed to fetch assignments, falling back to mocks:",
      err
    );

    return mockAssignments;
  }
}
