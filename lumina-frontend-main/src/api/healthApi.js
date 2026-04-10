import client from "./client";
import mockHealth from "../mocks/health.json";

const USE_MOCKS = true;

export async function fetchHealth() {
  // TEMP: use mock data until backend health endpoint is ready
  if (USE_MOCKS) {
    return mockHealth;
  }

  // TODO(Person 2): confirm health endpoint path
  // TODO(Person 2): confirm response shape for overall service health
  const response = await client.get("/health");
  return response.data;
}