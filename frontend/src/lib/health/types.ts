import { post } from "@/src/api";

// Normalized health record shared by the iOS HealthKit adapter and the
// Android Health Connect adapter (see ./native-adapters.md for details).
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

export type HealthSummary = {
  connected: boolean;
  steps: number;
  sleep_minutes: number;
  active_calories: number;
  source: string;
  records: number;
};

export async function syncHealthRecords(records: HealthRecord[]) {
  if (!records.length) return { received: 0, upserted: 0 };
  return post<{ received: number; upserted: number }>("/health/sync", records);
}
