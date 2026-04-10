import { useEffect, useState } from "react";
import { fetchAssignments, fetchNodes } from "../api/nodesApi";

export default function useNodePolling(intervalMs = 3000) {
  const [nodes, setNodes] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let intervalId;

    async function load() {
      try {
        const [nodesResult, assignmentsResult] = await Promise.all([
          fetchNodes(),
          fetchAssignments(),
        ]);

        setNodes(nodesResult.nodes || []);
        setAssignments(assignmentsResult.assignments || []);
        setError("");
      } catch (err) {
        console.error(err);
        setError("Failed to load cluster data.");
      } finally {
        setLoading(false);
      }
    }

    load();
    intervalId = setInterval(load, intervalMs);

    return () => clearInterval(intervalId);
  }, [intervalMs]);

  return { nodes, assignments, loading, error };
}