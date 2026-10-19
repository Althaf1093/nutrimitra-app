import Constants from "expo-constants";
import { copy } from "@/src/i18n";
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

// Text for errors raised here, in the language the person chose (api() runs outside the language context).
async function messages() {
  const stored = await storage.getItem<string>("nutrimitra.lang", "");
  return copy[stored === "te" ? "te" : "en"];
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken();
  // Only sign-in and a few public routes work without a token. Asking for anything else would just come back 401 (and show
  // a red error in the console), which happens when a screen reloads in the moment after sign-out.
  if (!token && !path.startsWith("/auth/") && !path.startsWith("/ingredients")) {
    throw new ApiError((await messages()).signInToContinue, 401, "no_token");
  }
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api${path}`, { ...options, headers });
  } catch (err) {
    // fetch only throws when nothing came back at all: the backend is down, the address is wrong, or (in a browser)
    // CORS blocked the page. Say so plainly instead of the browser's bare "Failed to fetch".
    const origin = typeof window !== "undefined" && window.location ? window.location.origin : "this app";
    console.error(`[Wellstride] Could not reach the backend at ${baseUrl || "(EXPO_PUBLIC_BACKEND_URL is empty)"}. Check that it is running and that EXPO_PUBLIC_BACKEND_URL is right. In a browser, also check that the backend's CORS_ORIGINS allows ${origin}.`, err);
    throw new ApiError((await messages()).cannotReachServer, 0, "network");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    // FastAPI validation errors are a list of {msg}; show the first message.
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") throw new ApiError(detail[0].msg, response.status);
    const fallback = (await messages()).somethingWrong;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) throw new ApiError(detail.message || fallback, response.status, detail.code);
    throw new ApiError(typeof detail === "string" ? detail : fallback, response.status);
  }
  return body as T;
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });