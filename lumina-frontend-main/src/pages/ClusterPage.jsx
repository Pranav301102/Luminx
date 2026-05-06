import useNodePolling from "../hooks/useNodePolling";
import ErrorBanner from "../components/common/ErrorBanner";
import LoadingSpinner from "../components/common/LoadingSpinner";
import StatusBadge from "../components/common/StatusBadge";

export default function ClusterPage() {
  const { nodes, assignments, loading, error } = useNodePolling(3000);

  const activeNodes = nodes.filter((node) => node.status === "healthy");

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Cluster</h2>
          <p>
            Inspect active nodes, CPU/RAM usage, node sharing, and layer
            assignments.
          </p>
        </div>
      </div>

      <ErrorBanner message={error} />
      {loading && <LoadingSpinner text="Loading cluster data..." />}

      <div className="summary-grid">
        <div className="summary-card">
          <span>Total Nodes</span>
          <strong>{nodes.length}</strong>
        </div>

        <div className="summary-card">
          <span>Active Nodes</span>
          <strong>{activeNodes.length}</strong>
        </div>

        <div className="summary-card">
          <span>Inactive Nodes</span>
          <strong>{nodes.length - activeNodes.length}</strong>
        </div>
      </div>

      <div className="card">
        <h3>Node Tracker</h3>

        <table>
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Status</th>
              <th>CPU</th>
              <th>RAM</th>
              <th>RAM Used</th>
              <th>VRAM</th>
              <th>Latency</th>
              <th>Throughput</th>
              <th>Active Connections</th>
              <th>Sharing With</th>
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
                  <td>
                    {node.cpu_percent !== undefined && node.cpu_percent !== null
                      ? `${node.cpu_percent}%`
                      : "N/A"}
                  </td>
                  <td>
                    {node.ram_percent !== undefined && node.ram_percent !== null
                      ? `${node.ram_percent}%`
                      : "N/A"}
                  </td>
                  <td>
                    {node.ram_used_gb !== undefined &&
                    node.ram_used_gb !== null &&
                    node.ram_total_gb !== undefined &&
                    node.ram_total_gb !== null
                      ? `${node.ram_used_gb} GB / ${node.ram_total_gb} GB`
                      : "N/A"}
                  </td>
                  <td>{node.vram ?? "N/A"}</td>
                  <td>
                    {node.latency_ms !== undefined && node.latency_ms !== null
                      ? `${node.latency_ms} ms`
                      : "N/A"}
                  </td>
                  <td>
                    {node.throughput_tps !== undefined &&
                    node.throughput_tps !== null
                      ? `${node.throughput_tps} tok/s`
                      : "N/A"}
                  </td>
                  <td>{node.active_connections ?? 0}</td>
                  <td>
                    {node.shared_with?.length > 0
                      ? node.shared_with.join(", ")
                      : "None"}
                  </td>
                  <td>{node.last_heartbeat ?? "N/A"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="11">No nodes available.</td>
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
    </div>
  );
}