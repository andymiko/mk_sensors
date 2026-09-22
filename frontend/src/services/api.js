const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function authHeaders(headers = {}) {
  const result = new Headers(headers);
  const token = localStorage.getItem("baseproject_token");
  if (token) result.set("Authorization", `Bearer ${token}`);
  return result;
}

export async function apiRequest(path, options = {}) {
  const headers = authHeaders(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload =
    response.status === 204
      ? null
      : contentType.includes("application/json")
        ? await response.json()
        : await response.text();
  if (!response.ok)
    throw new ApiError(
      payload?.detail || payload || "Не удалось выполнить запрос",
      response.status,
      payload,
    );
  return payload;
}
