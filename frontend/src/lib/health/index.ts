import { Platform } from "react-native";

import type { HealthStatus } from "./types";

export type { HealthRecord, HealthStatus, HealthSummary } from "./types";
export { syncHealthRecords } from "./types";

// Web / fallback entry point: browsers can never reach HealthKit or Health
// Connect, so the adapter reports an honest unsupported state.
export function getHealthStatus(): HealthStatus {
  if (Platform.OS === "web") return "web-unsupported";
  return "native-build-required";
}

export async function syncDeviceHealth(): Promise<{ synced: number } | null> {
  return null;
}
