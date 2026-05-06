import { useEffect, useState } from "react";
import { fetchAssignments, fetchNodes } from "../api/nodesApi";
import { addFrontendLog } from "../utils/frontendLogger";

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

        const loadedNodes = nodesResult.nodes || [];
        const loadedAssignments =
          assignmentsResult.assignments || [];

        setNodes(loadedNodes);
        setAssignments(loadedAssignments);
        setError("");

        // Frontend logging
        addFrontendLog(
          "info",
          "Cluster data refreshed",
          {
            nodeCount: loadedNodes.length,
            assignmentCount: loadedAssignments.length,
            activeNodes: loadedNodes.filter(
              (node) => node.status === "healthy"
            ).length,
          }
        );
      } catch (err) {
        console.error(err);

        setError("Failed to load cluster data.");

        // Error logging
        addFrontendLog(
          "error",
          "Failed to load cluster data",
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
    nodes,
    assignments,
    loading,
    error,
  };
}