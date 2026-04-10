import useNodePolling from "../hooks/useNodePolling";
import ErrorBanner from "../components/common/ErrorBanner";
import LoadingSpinner from "../components/common/LoadingSpinner";
import StatusBadge from "../components/common/StatusBadge";

export default function ClusterPage() {
  const { nodes, assignments, loading, error } = useNodePolling(3000);

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Cluster</h2>
          <p>Inspect active nodes, health, and layer assignments.</p>
        </div>
      </div>

      <ErrorBanner message={error} />
      {loading && <LoadingSpinner text="Loading cluster data..." />}

      <div className="card">
        <h3>Nodes</h3>
        <table>
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Status</th>
              <th>VRAM</th>
              <th>Latency</th>
              <th>Throughput</th>
              <th>Last Heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {nodes.length > 0 ? (
              nodes.map((node) => (
                <tr key={node.node_id}>
                  <td>{node.node_id}</td>
                  <td>
                    <StatusBadge status={node.status} />
                  </td>
                  <td>{node.vram}</td>
                  <td>{node.latency_ms} ms</td>
                  <td>{node.throughput_tps} tok/s</td>
                  <td>{node.last_heartbeat}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6">No nodes available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Layer Assignments</h3>
        <table>
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Layer Start</th>
              <th>Layer End</th>
            </tr>
          </thead>
          <tbody>
            {assignments.length > 0 ? (
              assignments.map((assignment, index) => (
                <tr key={`${assignment.node_id}-${index}`}>
                  <td>{assignment.node_id}</td>
                  <td>{assignment.layer_start}</td>
                  <td>{assignment.layer_end}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3">No assignments available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Integration Notes</h3>
        <ul>
          <li>TODO(Person 2): confirm final node scoring fields from backend.</li>
          <li>TODO(Person 2): confirm heartbeat freshness threshold for UI warnings.</li>
          <li>TODO(Person 2): confirm if cluster updates use polling, SSE, or WebSocket.</li>
        </ul>
      </div>
    </div>
  );
}