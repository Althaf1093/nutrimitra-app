import { Platform } from "react-native";

import type { HealthAdapter, HealthRecord, HealthStatus } from "./types";
import { syncHealthRecords } from "./types";

export type { HealthRecord, HealthStatus, HealthSummary } from "./types";
export { syncHealthRecords } from "./types";

let cachedAdapter: HealthAdapter | null | undefined;

// Native health modules contain custom native code: they exist only in an
// installed dev/production build, never in Expo Go. Lazy try/catch requires
// keep the Expo Go preview alive (Metro treats these as optional requires and
// module factories only execute on first call).
function loadAdapter(): HealthAdapter | null {
  if (cachedAdapter !== undefined) return cachedAdapter;
  cachedAdapter = null;
  try {
    if (Platform.OS === "ios") {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const hk = require("@kingstinct/react-native-healthkit");
      cachedAdapter = createIosAdapter(hk);
    } else if (Platform.OS === "android") {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const hc = require("react-native-health-connect");
      cachedAdapter = createAndroidAdapter(hc);
    }
  } catch {
    cachedAdapter = null;
  }
  return cachedAdapter;
}

export function getHealthStatus(): HealthStatus {
  return loadAdapter() ? "ready" : "native-build-required";
}

// Reads the last 24h of device activity (steps, distance, active calories,
// workouts, sleep) and syncs normalized records to the backend. Returns null
// when no adapter is available (Expo Go / permission denied).
export async function syncDeviceHealth(): Promise<{ synced: number } | null> {
  const adapter = loadAdapter();
  if (!adapter) return null;
  try {
    if (!(await adapter.available())) return null;
    await adapter.authorize();
    const records = await adapter.read(new Date(Date.now() - 24 * 60 * 60 * 1000), new Date());
    const result = await syncHealthRecords(records);
    return { synced: result.received };
  } catch {
    return null;
  }
}

function createIosAdapter(hk: {
  isHealthDataAvailable: () => Promise<boolean>;
  requestAuthorization: (args: { toRead: string[]; toShare: string[] }) => Promise<unknown>;
  queryQuantitySamples: (type: string, options: unknown) => Promise<Array<Record<string, unknown>>>;
  queryCategorySamples: (type: string, options: unknown) => Promise<Array<Record<string, unknown>>>;
  queryWorkoutSamples: (options: unknown) => Promise<Array<Record<string, unknown>>>;
}): HealthAdapter {
  const READ = [
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKWorkoutTypeIdentifier",
  ];
  return {
    available: async () => {
      try {
        return !!(await hk.isHealthDataAvailable());
      } catch {
        return false;
      }
    },
    authorize: async () => {
      await hk.requestAuthorization({ toRead: READ, toShare: [] });
    },
    read: async (from: Date, to: Date) => {
      const range = { from, to };
      const [steps, distance, calories, sleep, workouts] = await Promise.all([
        hk.queryQuantitySamples("HKQuantityTypeIdentifierStepCount", range),
        hk.queryQuantitySamples("HKQuantityTypeIdentifierDistanceWalkingRunning", range),
        hk.queryQuantitySamples("HKQuantityTypeIdentifierActiveEnergyBurned", range),
        hk.queryCategorySamples("HKCategoryTypeIdentifierSleepAnalysis", { ...range, limit: 0 }),
        hk.queryWorkoutSamples({ filter: { date: range }, limit: 0 }),
      ]);
      const records: HealthRecord[] = [];
      for (const x of steps ?? []) records.push({ externalId: String(x.uuid), metric: "steps", start: String(x.startDate), end: String(x.endDate), value: Number(x.quantity), unit: "count", source: String((x as { sourceRevision?: { source?: string } }).sourceRevision?.source ?? "") });
      for (const x of distance ?? []) records.push({ externalId: String(x.uuid), metric: "distance", start: String(x.startDate), end: String(x.endDate), value: Number(x.quantity), unit: "m", source: String((x as { sourceRevision?: { source?: string } }).sourceRevision?.source ?? "") });
      for (const x of calories ?? []) records.push({ externalId: String(x.uuid), metric: "activeCalories", start: String(x.startDate), end: String(x.endDate), value: Number(x.quantity), unit: "kcal", source: String((x as { sourceRevision?: { source?: string } }).sourceRevision?.source ?? "") });
      for (const x of sleep ?? []) records.push({ externalId: String(x.uuid), metric: "sleep", start: String(x.startDate), end: String(x.endDate), type: String(x.value), source: String((x as { sourceRevision?: { source?: string } }).sourceRevision?.source ?? "") });
      for (const x of workouts ?? []) records.push({ externalId: String(x.uuid), metric: "workout", start: String(x.startDate), end: String(x.endDate), type: String(x.workoutActivityType), value: Number(x.totalEnergyBurned ?? 0), unit: "kcal" });
      return records;
    },
  };
}

function createAndroidAdapter(hc: {
  initialize: () => Promise<boolean>;
  requestPermission: (permissions: Array<{ accessType: string; recordType: string }>) => Promise<unknown>;
  readRecords: (type: string, options: unknown) => Promise<{ records?: Array<Record<string, never>> }>;
}): HealthAdapter {
  const permissions = [
    { accessType: "read", recordType: "Steps" },
    { accessType: "read", recordType: "Distance" },
    { accessType: "read", recordType: "ActiveCaloriesBurned" },
    { accessType: "read", recordType: "ExerciseSession" },
    { accessType: "read", recordType: "SleepSession" },
  ];
  const filter = (from: Date, to: Date) => ({ timeRangeFilter: { operator: "between", startTime: from.toISOString(), endTime: to.toISOString() } });
  return {
    available: async () => {
      try {
        return !!(await hc.initialize());
      } catch {
        return false;
      }
    },
    authorize: async () => {
      await hc.requestPermission(permissions);
    },
    read: async (from: Date, to: Date) => {
      const [steps, distance, calories, workouts, sleep] = await Promise.all([
        hc.readRecords("Steps", filter(from, to)),
        hc.readRecords("Distance", filter(from, to)),
        hc.readRecords("ActiveCaloriesBurned", filter(from, to)),
        hc.readRecords("ExerciseSession", filter(from, to)),
        hc.readRecords("SleepSession", filter(from, to)),
      ]);
      const records: HealthRecord[] = [];
      for (const x of (steps as { records?: Array<Record<string, any>> })?.records ?? []) records.push({ externalId: x.metadata.id, metric: "steps", start: x.startTime, end: x.endTime, value: Number(x.count), unit: "count", source: x.metadata.dataOrigin });
      for (const x of (distance as { records?: Array<Record<string, any>> })?.records ?? []) records.push({ externalId: x.metadata.id, metric: "distance", start: x.startTime, end: x.endTime, value: Number(x.distance.inMeters), unit: "m", source: x.metadata.dataOrigin });
      for (const x of (calories as { records?: Array<Record<string, any>> })?.records ?? []) records.push({ externalId: x.metadata.id, metric: "activeCalories", start: x.startTime, end: x.endTime, value: Number(x.energy.inKilocalories), unit: "kcal", source: x.metadata.dataOrigin });
      for (const x of (workouts as { records?: Array<Record<string, any>> })?.records ?? []) records.push({ externalId: x.metadata.id, metric: "workout", start: x.startTime, end: x.endTime, type: String(x.exerciseType), source: x.metadata.dataOrigin });
      for (const x of (sleep as { records?: Array<Record<string, any>> })?.records ?? []) records.push({ externalId: x.metadata.id, metric: "sleep", start: x.startTime, end: x.endTime, type: "sleep", source: x.metadata.dataOrigin });
      return records;
    },
  };
}
