## Files Each Teammate Should Change

### Person 1 — Core Inference Lead
Person 1 should only change:

- `src/api/requestsApi.js`

What Person 1 should do:
- connect `/generate`
- connect `/generate/stream`
- define request payload format
- define response parsing
- define streaming chunk parsing
- confirm inference latency fields used by frontend

---

### Person 2 — Distributed Systems Lead
Person 2 should only change:

- `src/api/nodesApi.js`
- `src/api/healthApi.js`
- `src/api/requestsApi.js`  <!-- only for trace endpoint -->

What Person 2 should do:
- connect `/nodes/list`
- connect `/assignments/current`
- connect `/health`
- connect `/requests/trace`
- define node response schema
- define assignment response schema
- define health response schema
- define trace response schema

---

### Person 4 — Deployment and SRE Lead
Person 4 should only change:

- `.env`
- `.env.example`
- `src/api/client.js`  <!-- only if base URL / proxy config must be updated -->

What Person 4 should do:
- set `VITE_API_BASE_URL`
- provide staging and production API URLs
- configure reverse proxy path if needed
- confirm deployed backend connection settings

---
### .env file (You should make changes in this files)
```bash
# Example environment configuration for Lumina frontend

# Backend API base URL
# Replace with your local or deployed backend URL
VITE_API_BASE_URL=http://localhost:8000

# Enable or disable streaming mode
# true = use streaming API
# false = use normal API
VITE_ENABLE_STREAMING=true

# Log level (optional)
# options: debug | info | warn | error
VITE_LOG_LEVEL=debug
```
---

## Files Teammates Should Not Change

These files should stay under Person 3 frontend ownership:

- `src/main.jsx`
- `src/App.jsx`
- `src/pages/ChatPage.jsx`
- `src/pages/ClusterPage.jsx`
- `src/pages/HealthPage.jsx`
- `src/pages/TracePage.jsx`
- `src/components/layout/*`
- `src/components/common/*`
- `src/hooks/*`
- `src/styles/*`
- `src/mocks/*`
