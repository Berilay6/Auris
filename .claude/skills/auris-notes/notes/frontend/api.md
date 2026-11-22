# frontend/src/api

Code: `frontend/src/api/` · Related: every backend route the frontend calls

The browser talks only to the frontend origin. Vite (in development) and
Nginx (in Docker) forward every path that starts with `/api` to the FastAPI
backend. The `/api` prefix is not removed on the way.

## Rules

- Send every backend request through `get` or `post` in
  `frontend/src/api/client.js`. Never call `fetch` directly in components or hooks.
- Pass paths without the `/api` prefix, for example `get('/health')`. The client
  adds the prefix. Never write a host name such as `http://localhost:8000`.
- A failed request throws `ApiError`. Its `status` is the HTTP status code, or
  `null` when no response arrived.
- The client reads responses with `response.json()`. An empty body (for example
  HTTP 204) is not supported yet. Change the client before you add such an endpoint.
- Backend: every route must be under `/api`. The health route is `GET /api/health`
  and returns HTTP 200 with a JSON body (for example `{"status": "ok"}`) when the
  API is up. The status badge does not read the fields of the body, but the body
  must be valid JSON, because the client calls `response.json()`.

## Decision log

| Date | Task | Decision | Who |
|---|---|---|---|
| 2026-11-22 | SCRUM-20 | All frontend API calls go through `client.js` with `/api` paths | Kaan |
| 2026-11-22 | SCRUM-20 | Health route is `GET /api/health`; any 2xx means "API up" | Kaan |
| 2026-11-22 | SCRUM-20 | Correction: the health response must also be valid JSON (the client calls `response.json()`) | Kaan |
