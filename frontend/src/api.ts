import Constants from "expo-constants";
import { storage } from "@/src/utils/storage";

const configuredUrl = Constants.expoConfig?.extra?.backendUrl as string | undefined;
const baseUrl = (configuredUrl || process.env.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_BACKEND_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "nutrimitra.session.token";

export async function getToken() {
  return storage.secureGet(TOKEN_KEY, "");
}

export async function saveToken(token: string) {
  return storage.secureSet(TOKEN_KEY, token);
}

export async function clearToken() {
  return storage.secureRemove(TOKEN_KEY);
}

// Errors carry the HTTP status and, for structured errors such as {"code": "ai_busy", "message": ...}, the code.
export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export const isAiBusy = (err: unknown) => err instanceof ApiError && err.code === "ai_busy";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${baseUrl}/api${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) throw new ApiError(detail.message || "Something went wrong", response.status, detail.code);
    throw new ApiError(typeof detail === "string" ? detail : "Something went wrong", response.status);
  }
  return body as T;
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });