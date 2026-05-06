import { useEffect, useState } from "react";
import { fetchHealth } from "../api/healthApi";
import { addFrontendLog } from "../utils/frontendLogger";

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

        // Frontend logging
        addFrontendLog(
          "info",
          "Health data refreshed",
          {
            trackerStatus: result.tracker_status,
            inferenceApiStatus:
              result.inference_api_status,
            clusterStatus: result.cluster_status,
          }
        );
      } catch (err) {
        console.error(err);

        setError("Failed to load health data.");

        // Error logging
        addFrontendLog(
          "error",
          "Failed to load health data",
          {
            error: err.message,
          }
        );
      } finally {
        setLoading(false);
      }
    }

    load();

    intervalId = setInterval(load, intervalMs);

    return () => clearInterval(intervalId);
  }, [intervalMs]);

  return {
    data,
    loading,
    error,
  };
}