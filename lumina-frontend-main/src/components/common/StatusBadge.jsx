export default function StatusBadge({ status }) {
  const normalized = (status || "").toLowerCase();

  let className = "status-badge";
  if (normalized === "healthy" || normalized === "online" || normalized === "ok") {
    className += " status-good";
  } else if (normalized === "degraded" || normalized === "warning") {
    className += " status-warn";
  } else {
    className += " status-bad";
  }

  return <span className={className}>{status || "unknown"}</span>;
}