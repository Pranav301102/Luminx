import { useEffect, useState } from "react";
import { fetchHealth } from "../api/healthApi";

export default function useHealthPolling(intervalMs = 3000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let intervalId;

    async function load() {
      try {
        const result = await fetchHealth();
        setData(result);
        setError("");
      } catch (err) {
        console.error(err);
        setError("Failed to load health data.");
      } finally {
        setLoading(false);
      }
    }

    load();
    intervalId = setInterval(load, intervalMs);

    return () => clearInterval(intervalId);
  }, [intervalMs]);

  return { data, loading, error };
}