// Thin JSON client for /api/v1 with the server's {error: {code, message}} envelope.
import { setState } from "./state.js";

export class ApiError extends Error {
  constructor(status, code, message, fields = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network", "Network error. Check your connection and retry.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = data.error || {};
    throw new ApiError(
      response.status,
      err.code || "error",
      err.message || "Request failed.",
      err.fields,
    );
  }
  if (typeof data.offline_ai === "boolean") setState({ aiOffline: data.offline_ai });
  if (data.ai_mode) setState({ aiOffline: data.ai_mode === "offline" });
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body = {}) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
};
