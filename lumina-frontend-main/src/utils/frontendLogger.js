const LOG_KEY = "lumina_frontend_logs";
const MAX_LOGS = 150;

export function addFrontendLog(level, message, metadata = {}) {
  const log = {
    id: crypto.randomUUID(),
    level,
    message,
    metadata,
    timestamp: new Date().toISOString(),
  };

  const existingLogs = JSON.parse(
    localStorage.getItem(LOG_KEY) || "[]"
  );

  const updatedLogs = [log, ...existingLogs].slice(0, MAX_LOGS);

  localStorage.setItem(LOG_KEY, JSON.stringify(updatedLogs));
}

export function getFrontendLogs() {
  return JSON.parse(localStorage.getItem(LOG_KEY) || "[]");
}

export function clearFrontendLogs() {
  localStorage.removeItem(LOG_KEY);
}