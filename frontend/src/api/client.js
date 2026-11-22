/**
 * Small HTTP client for the Auris backend.
 *
 * All requests use paths that start with /api. Vite (in development) and
 * Nginx (in Docker) forward these requests to the FastAPI backend, so this
 * code never needs the backend host name.
 */

const API_PREFIX = '/api';

/**
 * Error for a failed API request.
 * `status` is the HTTP status code, or null if no response was received.
 */
export class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(method, path, body) {
  const url = API_PREFIX + path;
  const options = { method };
  if (body !== undefined) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch {
    // fetch() rejects only when no HTTP response arrives at all.
    throw new ApiError(`Cannot reach the backend: ${method} ${url}`);
  }

  if (!response.ok) {
    throw new ApiError(
      `API request failed: ${method} ${url} (${response.status})`,
      response.status,
    );
  }

  return response.json();
}

/** Sends a GET request and returns the parsed JSON body. */
export function get(path) {
  return request('GET', path);
}

/** Sends a POST request with a JSON body and returns the parsed JSON body. */
export function post(path, body) {
  return request('POST', path, body);
}
