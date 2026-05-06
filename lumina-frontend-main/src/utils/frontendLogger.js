const LOG_KEY = "lumina_frontend_logs";
const MAX_LOGS = 150;

export function addFrontendLog(level, message, metadata = {}) {
  // Fallback for non-HTTPS environments where crypto.randomUUID is undefined
  const generateId = () => {
    return typeof crypto !== 'undefined' && crypto.randomUUID 
      ? crypto.randomUUID() 
      : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  };

  const log = {
    id: generateId(),
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