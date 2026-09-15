import { Platform } from "react-native";

import { post } from "@/src/api";

// Normalized health record shared by the iOS HealthKit adapter and the
// Android Health Connect adapter (see ./health/native-adapters.md for the
// native implementations that plug into this contract in an installed build).
export type Metric = "steps" | "distance" | "activeCalories" | "workout" | "sleep";

export type HealthRecord = {
  externalId: string;
  metric: Metric;
  start: string;
  end: string;
  value?: number;
  unit?: "count" | "m" | "kcal";
  type?: string;
  source?: string;
};

export interface HealthAdapter {
  available(): Promise<boolean>;
  authorize(): Promise<void>;
  read(from: Date, to: Date): Promise<HealthRecord[]>;
}

export type HealthStatus = "web-unsupported" | "native-build-required" | "ready";

// The native modules (@kingstinct/react-native-healthkit on iOS,
// react-native-health-connect on Android) contain custom native code and only
// load in an installed development/production build — never in Expo Go or web.
// They are resolved lazily at runtime so the preview keeps working.
export function getHealthStatus(): HealthStatus {
  if (Platform.OS === "web") return "web-unsupported";
  return "native-build-required";
}

export async function syncHealthRecords(records: HealthRecord[]) {
  if (!records.length) return { received: 0, upserted: 0 };
  return post<{ received: number; upserted: number }>("/health/sync", records);
}
