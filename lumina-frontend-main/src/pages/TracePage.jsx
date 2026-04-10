import { useState } from "react";
import { fetchRequestTrace } from "../api/requestsApi";
import ErrorBanner from "../components/common/ErrorBanner";

export default function TracePage() {
  const [requestId, setRequestId] = useState("");
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLookup(e) {
    e.preventDefault();

    if (!requestId.trim()) return;

    setLoading(true);
    setError("");
    setTrace(null);

    try {
      // TODO(Person 2): verify trace lookup route and schema
      const result = await fetchRequestTrace(requestId);
      setTrace(result);
    } catch (err) {
      console.error(err);
      setError("Failed to load trace.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Trace</h2>
          <p>Review request lifecycle and latency breakdown.</p>
        </div>
      </div>

      <ErrorBanner message={error} />

      <form className="card" onSubmit={handleLookup}>
        <label className="input-label">Request ID</label>
        <input
          type="text"
          placeholder="Enter request ID"
          value={requestId}
          onChange={(e) => setRequestId(e.target.value)}
        />

        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Load Trace"}
        </button>
      </form>

      <div className="card">
        <h3>Trace Details</h3>
        <pre>{trace ? JSON.stringify(trace, null, 2) : "No trace loaded."}</pre>
      </div>

      <div className="card">
        <h3>Integration Notes</h3>
        <ul>
          <li>TODO(Person 2): confirm final trace event names.</li>
          <li>TODO(Person 1): confirm inference-stage latency fields.</li>
          <li>TODO(Person 2): confirm failover / retry event visibility for Phase 3.</li>
        </ul>
      </div>
    </div>
  );
}