import { useState } from "react";

export default function useStreamGenerate() {
  const [streamText, setStreamText] = useState("");
  const [loading, setLoading] = useState(false);

  async function startStream(prompt) {
    setLoading(true);
    setStreamText("");

    try {
      const response = await fetch("http://localhost:8000/generate/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.body) {
        throw new Error("Streaming not supported by response.");
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
        setStreamText((prev) => prev + chunk);
      }
    } catch (error) {
      console.error(error);
      setStreamText("Streaming failed.");
    } finally {
      setLoading(false);
    }
  }

  return {
    streamText,
    loading,
    startStream,
  };
}