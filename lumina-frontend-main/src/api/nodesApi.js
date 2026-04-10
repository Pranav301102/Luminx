import client from "./client";
import mockNodes from "../mocks/nodes.json";
import mockAssignments from "../mocks/assignments.json";

const USE_MOCKS = true;

export async function fetchNodes() {
  // TEMP: mock node list during early frontend development
  if (USE_MOCKS) {
    return mockNodes;
  }

  // TODO(Person 2): confirm /nodes/list route and final node DTO fields
  // ASSUMPTION: response = { nodes: [...] }
  const response = await client.get("/nodes/list");
  return response.data;
}

export async function fetchAssignments() {
  // TEMP: mock assignment list during early frontend development
  if (USE_MOCKS) {
    return mockAssignments;
  }

  // TODO(Person 2): confirm /assignments/current route and response DTO
  // ASSUMPTION: response = { assignments: [...] }
  const response = await client.get("/assignments/current");
  return response.data;
}