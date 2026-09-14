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

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${baseUrl}/api${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong");
  return body as T;
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });