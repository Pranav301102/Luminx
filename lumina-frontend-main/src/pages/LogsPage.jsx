import { useEffect, useState } from "react";
import {
  clearFrontendLogs,
  getFrontendLogs,
} from "../utils/frontendLogger";

export default function LogsPage() {
  const [logs, setLogs] = useState([]);

  function loadLogs() {
    setLogs(getFrontendLogs());
  }

  function handleClearLogs() {
    clearFrontendLogs();
    setLogs([]);
  }

  useEffect(() => {
    loadLogs();

    const intervalId = setInterval(loadLogs, 2000);

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Frontend Logs</h2>
          <p>
            Review frontend polling, API fallback, and dashboard
            activity logs.
          </p>
        </div>

        <button className="secondary-button" onClick={handleClearLogs}>
          Clear Logs
        </button>
      </div>

      <div className="card">
        <h3>Recent Logs</h3>

        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Level</th>
              <th>Message</th>
              <th>Metadata</th>
            </tr>
          </thead>

          <tbody>
            {logs.length > 0 ? (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <StatusText level={log.level} />
                  </td>
                  <td>{log.message}</td>
                  <td>
                    <pre>
                      {JSON.stringify(log.metadata, null, 2)}
                    </pre>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4">No frontend logs available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusText({ level }) {
  return (
    <span>
      {level || "info"}
    </span>
  );
}