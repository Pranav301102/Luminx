import client from "./client";
import mockTrace from "../mocks/trace.json";

const USE_MOCKS = true;

export async function generateText(payload) {
  // TODO(Person 1): confirm request body schema for generation endpoint
  // ASSUMPTION: payload includes { prompt, stream }
  // TODO(Person 1): confirm final response fields: request_id, output, finish_reason, latency_ms
  const response = await client.post("/generate", payload);
  return response.data;
}

export async function fetchRequestTrace(requestId) {
  if (USE_MOCKS) {
    return {
      ...mockTrace,
      request_id: requestId || mockTrace.request_id,
    };
  }

  // TODO(Person 2): confirm trace endpoint path and accepted query params
  // TODO(Person 2): confirm trace step fields for timeline and latency breakdown
  const response = await client.get("/requests/trace", {
    params: { request_id: requestId },
  });

  return response.data;
}

export async function streamGenerate(prompt, onChunk) {
  // TODO(Person 1): confirm whether streaming uses fetch chunks, SSE, or WebSocket
  // TODO(Person 1): confirm exact chunk format
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/generate/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    }
  );

  if (!response.body) {
    throw new Error("Streaming response body is not available.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let done = false;

  while (!done) {
    const result = await reader.read();
    done = result.done;

    const chunk = decoder.decode(result.value || new Uint8Array(), {
      stream: !done,
    });

    if (chunk && onChunk) {
      onChunk(chunk);
    }
  }
}