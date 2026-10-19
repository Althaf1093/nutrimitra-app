import { Platform } from "react-native";
import type * as NotificationsModule from "expo-notifications";

import type { Lang } from "@/src/i18n";
import type { ReminderPrefs } from "@/src/types";

// Reminders are native-only, and merely importing expo-notifications logs "Listening to push token changes is not yet
// fully supported on web" in the browser, so the package is loaded on devices only.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Notifications: typeof NotificationsModule = Platform.OS === "web" ? (undefined as never) : require("expo-notifications");

if (Platform.OS !== "web") {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

export type PermissionResult = "granted" | "denied" | "blocked" | "unsupported";

export function remindersSupported(): boolean {
  return Platform.OS !== "web";
}

export async function ensureReminderPermissions(): Promise<PermissionResult> {
  if (Platform.OS === "web") return "unsupported";
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("reminders", {
      name: "Reminders",
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
  const current = await Notifications.getPermissionsAsync();
  const iosOk = (status: NotificationsModule.NotificationPermissionsStatus) =>
    Platform.OS !== "ios" ||
    status.ios?.status === Notifications.IosAuthorizationStatus.AUTHORIZED ||
    status.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;
  if (current.status === "granted" && iosOk(current)) return "granted";
  if (!current.canAskAgain) return "blocked";
  const asked = await Notifications.requestPermissionsAsync();
  if (asked.status === "granted" && iosOk(asked)) return "granted";
  return asked.canAskAgain ? "denied" : "blocked";
}

const text: Record<Lang, Record<string, [string, string]>> = {
  en: {
    breakfast: ["Breakfast time", "A protein-rich start keeps your energy steady."],
    lunch: ["Lunch time", "Half colourful vegetables, a quarter protein, a quarter whole grains."],
    dinner: ["Dinner time", "Keep it light and comforting tonight."],
    water: ["Hydration", "Have a glass of water."],
    move: ["Move a little", "Stand up and stretch for a minute."],
    weekly: ["Weekly review", "Look back at your week — kindly, not critically."],
  },
  te: {
    breakfast: ["అల్పాహార సమయం", "ప్రోటీన్‌తో మంచి ప్రారంభం శక్తిని స్థిరంగా ఉంచుతుంది."],
    lunch: ["మధ్యాహ్న భోజనం", "సగం కూరగాయలు, పావు వంతు ప్రోటీన్, పావు వంతు ధాన్యాలు."],
    dinner: ["రాత్రి భోజనం", "ఈ రాత్రి తేలికపాటి భోజనం చేయండి."],
    water: ["నీరు త్రాగండి", "ఒక గ్లాసు నీరు త్రాగండి."],
    move: ["కొంచెం కదలండి", "లేచి ఒక నిమిషం కదలండి."],
    weekly: ["వారపు సమీక్ష", "మీ వారాన్ని ప్రేమతో పరిశీలించండి."],
  },
};

async function scheduleDaily(title: string, body: string, hour: number, minute: number) {
  return Notifications.scheduleNotificationAsync({
    content: { title, body, sound: "default", ...(Platform.OS === "android" ? { channelId: "reminders" } : {}) },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour, minute },
  });
}

async function scheduleInterval(title: string, body: string, seconds: number) {
  return Notifications.scheduleNotificationAsync({
    content: { title, body, sound: "default", ...(Platform.OS === "android" ? { channelId: "reminders" } : {}) },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds, repeats: true },
  });
}

export async function applyReminders(prefs: ReminderPrefs, lang: Lang) {
  if (Platform.OS === "web") return;
  await Notifications.cancelAllScheduledNotificationsAsync();
  const L = text[lang] || text.en;
  if (prefs.meals) {
    await scheduleDaily(...L.breakfast, 8, 0);
    await scheduleDaily(...L.lunch, 13, 0);
    await scheduleDaily(...L.dinner, 19, 30);
  }
  if (prefs.hydration) await scheduleInterval(...L.water, 3 * 60 * 60);
  if (prefs.movement) await scheduleInterval(...L.move, 2 * 60 * 60);
  if (prefs.weekly) {
    await Notifications.scheduleNotificationAsync({
      content: { title: L.weekly[0], body: L.weekly[1], sound: "default", ...(Platform.OS === "android" ? { channelId: "reminders" } : {}) },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.WEEKLY, weekday: 1, hour: 18, minute: 0 },
    });
  }
}

export async function clearReminders() {
  if (Platform.OS === "web") return;
  await Notifications.cancelAllScheduledNotificationsAsync();
}
