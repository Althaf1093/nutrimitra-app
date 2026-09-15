# Native health adapters (installed iOS/Android builds only)

HealthKit and Health Connect contain custom native code. They do **not** run in
Expo Go or on web, so these packages are intentionally not part of the preview
bundle. When generating a native build (Publish → iOS/Android build), install
and wire the adapters below; both implement `HealthAdapter` from
`../health.ts`, and their records upload through `syncHealthRecords()` →
`POST /api/health/sync`.

## Install (build time only)

```bash
yarn expo install expo-dev-client
yarn expo install @kingstinct/react-native-healthkit react-native-nitro-modules
yarn add react-native-health-connect expo-build-properties
```

`app.json` already declares the iOS usage descriptions and the Android
`android.permission.health.READ_*` permissions. Enable the HealthKit
capability for the iOS App ID, then rebuild.

## iOS adapter (HealthKit)

```ts
// src/lib/health/ios.ts
import {
  isHealthDataAvailable, requestAuthorization,
  queryQuantitySamples, queryCategorySamples, queryWorkoutSamples,
} from "@kingstinct/react-native-healthkit";
import type { HealthAdapter, HealthRecord } from "../health";

const READ = [
  "HKQuantityTypeIdentifierStepCount",
  "HKQuantityTypeIdentifierDistanceWalkingRunning",
  "HKQuantityTypeIdentifierActiveEnergyBurned",
  "HKCategoryTypeIdentifierSleepAnalysis",
  "HKWorkoutTypeIdentifier",
] as const;

export const iosHealth: HealthAdapter = {
  available: async () => isHealthDataAvailable(),
  authorize: async () => { await requestAuthorization({ toRead: [...READ], toShare: [] }); },
  read: async (from, to): Promise<HealthRecord[]> => {
    const range = { from, to };
    const [steps, distance, calories, sleep, workouts] = await Promise.all([
      queryQuantitySamples("HKQuantityTypeIdentifierStepCount", range),
      queryQuantitySamples("HKQuantityTypeIdentifierDistanceWalkingRunning", range),
      queryQuantitySamples("HKQuantityTypeIdentifierActiveEnergyBurned", range),
      queryCategorySamples("HKCategoryTypeIdentifierSleepAnalysis", { ...range, limit: 0 }),
      queryWorkoutSamples({ filter: { date: range }, limit: 0 }),
    ]);
    return [
      ...steps.map((x: any) => ({ externalId: x.uuid, metric: "steps" as const, start: x.startDate, end: x.endDate, value: Number(x.quantity), unit: "count" as const, source: x.sourceRevision?.source })),
      ...distance.map((x: any) => ({ externalId: x.uuid, metric: "distance" as const, start: x.startDate, end: x.endDate, value: Number(x.quantity), unit: "m" as const, source: x.sourceRevision?.source })),
      ...calories.map((x: any) => ({ externalId: x.uuid, metric: "activeCalories" as const, start: x.startDate, end: x.endDate, value: Number(x.quantity), unit: "kcal" as const, source: x.sourceRevision?.source })),
      ...sleep.map((x: any) => ({ externalId: x.uuid, metric: "sleep" as const, start: x.startDate, end: x.endDate, type: String(x.value), source: x.sourceRevision?.source })),
      ...workouts.map((x: any) => ({ externalId: x.uuid, metric: "workout" as const, start: x.startDate, end: x.endDate, type: String(x.workoutActivityType), value: Number(x.totalEnergyBurned ?? 0), unit: "kcal" as const })),
    ];
  },
};
```

## Android adapter (Health Connect)

```ts
// src/lib/health/android.ts
import { initialize, requestPermission, readRecords } from "react-native-health-connect";
import type { HealthAdapter, HealthRecord } from "../health";

const permissions = [
  { accessType: "read", recordType: "Steps" },
  { accessType: "read", recordType: "Distance" },
  { accessType: "read", recordType: "ActiveCaloriesBurned" },
  { accessType: "read", recordType: "ExerciseSession" },
  { accessType: "read", recordType: "SleepSession" },
] as const;

const filter = (from: Date, to: Date) => ({
  timeRangeFilter: { operator: "between" as const, startTime: from.toISOString(), endTime: to.toISOString() },
});

export const androidHealth: HealthAdapter = {
  available: async () => initialize(),
  authorize: async () => { await requestPermission([...permissions]); },
  read: async (from, to) => {
    const [steps, distance, calories, workouts, sleep] = await Promise.all([
      readRecords("Steps", filter(from, to)),
      readRecords("Distance", filter(from, to)),
      readRecords("ActiveCaloriesBurned", filter(from, to)),
      readRecords("ExerciseSession", filter(from, to)),
      readRecords("SleepSession", filter(from, to)),
    ]);
    const records: HealthRecord[] = [];
    for (const x of (steps as any).records ?? []) records.push({ externalId: x.metadata.id, metric: "steps", start: x.startTime, end: x.endTime, value: Number(x.count), unit: "count", source: x.metadata.dataOrigin });
    for (const x of (distance as any).records ?? []) records.push({ externalId: x.metadata.id, metric: "distance", start: x.startTime, end: x.endTime, value: Number(x.distance.inMeters), unit: "m", source: x.metadata.dataOrigin });
    for (const x of (calories as any).records ?? []) records.push({ externalId: x.metadata.id, metric: "activeCalories", start: x.startTime, end: x.endTime, value: Number(x.energy.inKilocalories), unit: "kcal", source: x.metadata.dataOrigin });
    for (const x of (workouts as any).records ?? []) records.push({ externalId: x.metadata.id, metric: "workout", start: x.startTime, end: x.endTime, type: String(x.exerciseType), source: x.metadata.dataOrigin });
    for (const x of (sleep as any).records ?? []) records.push({ externalId: x.metadata.id, metric: "sleep", start: x.startTime, end: x.endTime, type: "sleep", source: x.metadata.dataOrigin });
    return records;
  },
};
```

## Notes

- Always `authorize()` before `read()`; re-check on every foreground sync.
- HealthKit never reveals read denials — treat empty results as unknown, not zero.
- Deduplicate by `externalId + source` (the backend upserts on this pair).
- Health Connect defaults to a 30-day history window before permission grant.
