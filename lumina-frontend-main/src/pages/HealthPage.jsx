import useHealthPolling from "../hooks/useHealthPolling";
import ErrorBanner from "../components/common/ErrorBanner";
import LoadingSpinner from "../components/common/LoadingSpinner";
import StatusBadge from "../components/common/StatusBadge";

export default function HealthPage() {
  const { data, loading, error } = useHealthPolling(3000);

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Health</h2>
          <p>Monitor global service health and readiness.</p>
        </div>
      </div>

      <ErrorBanner message={error} />
      {loading && <LoadingSpinner text="Loading health data..." />}

      {data && (
        <>
          <div className="card">
            <h3>System Overview</h3>
            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Tracker</span>
                <StatusBadge status={data.tracker_status} />
              </div>
              <div className="stat-box">
                <span className="stat-label">Inference API</span>
                <StatusBadge status={data.inference_api_status} />
              </div>
              <div className="stat-box">
                <span className="stat-label">Cluster</span>
                <StatusBadge status={data.cluster_status} />
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Raw Health Payload</h3>
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </div>
        </>
      )}
    </div>
  );
}