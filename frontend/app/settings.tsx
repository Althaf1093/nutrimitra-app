import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post, put } from "@/src/api";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { getHealthStatus } from "@/src/lib/health";
import { applyReminders, clearReminders, ensureReminderPermissions, remindersSupported } from "@/src/lib/notifications";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { ReminderPrefs } from "@/src/types";

function ToggleRow({ title, subtitle, value, onToggle, testID }: { title: string; subtitle: string; value: boolean; onToggle: () => void; testID: string }) {
  const styles = useStyles();
  return (
    <Pressable testID={testID} accessibilityRole="button" accessibilityLabel={title} onPress={onToggle} style={styles.settingRow}>
      <View style={styles.flex}>
        <Text style={styles.mealName}>{title}</Text>
        <Text style={styles.mutedText}>{subtitle}</Text>
      </View>
      <View style={[styles.switchTrack, value && styles.switchOn]}>
        <View style={[styles.switchKnob, value && styles.switchKnobOn]} />
      </View>
    </Pressable>
  );
}

type PermissionPrefs = { health_sync: boolean; wearables: boolean; analytics: boolean; coach_memory: boolean };

export default function SettingsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { lang, setLang, t, signOut, status } = useAuth();
  const [permission, setPermission] = useState<PermissionPrefs>({ health_sync: false, wearables: false, analytics: false, coach_memory: true });
  const [reminders, setReminders] = useState<ReminderPrefs>({ meals: true, hydration: false, movement: false, weekly: true });
  const [note, setNote] = useState("");

  useEffect(() => {
    if (status !== "ready") return;
    api<{ health_sync?: boolean; wearables?: boolean; analytics?: boolean; coach_memory?: boolean }>("/permissions")
      .then((prefs) => setPermission({ health_sync: !!prefs.health_sync, wearables: !!prefs.wearables, analytics: !!prefs.analytics, coach_memory: prefs.coach_memory !== false }))
      .catch(() => undefined);
    api<ReminderPrefs>("/reminders")
      .then((prefs) => setReminders({ meals: !!prefs.meals, hydration: !!prefs.hydration, movement: !!prefs.movement, weekly: !!prefs.weekly }))
      .catch(() => undefined);
  }, [status]);

  // Route guard: this modal requires an authenticated, onboarded session.
  if (status === "loading") {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }
  if (status !== "ready") {
    return <Redirect href={status === "onboarding" ? "/onboarding" : "/welcome"} />;
  }

  const updatePermission = async (key: keyof PermissionPrefs) => {
    const next = { ...permission, [key]: !permission[key] };
    setPermission(next);
    await post("/permissions", next).catch(() => undefined);
  };

  const updateReminder = async (key: keyof ReminderPrefs) => {
    setNote("");
    const next = { ...reminders, [key]: !reminders[key] };
    if (Object.values(next).some(Boolean) && remindersSupported()) {
      const result = await ensureReminderPermissions();
      if (result === "blocked") {
        setNote("blocked");
        return;
      }
      if (result === "denied") {
        setNote("denied");
        return;
      }
    }
    setReminders(next);
    await put("/reminders", next).catch(() => undefined);
    if (Object.values(next).some(Boolean)) await applyReminders(next, lang);
    else await clearReminders();
  };

  const healthStatus = getHealthStatus();

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="settings-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA</Text>
          <Text style={styles.headerTitle}>{t.settings}</Text>
        </View>
        <Pressable testID="settings-close" accessibilityRole="button" accessibilityLabel={t.close} onPress={() => router.back()} style={styles.iconButton}>
          <AppIcon name="xmark" color={colors.onSurface} size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        <View style={styles.syncCard} testID="health-status-card">
          <View style={styles.syncIcon}>
            <AppIcon name="heart.text.square.fill" color={styles.syncIconTint.color as string} size={22} />
          </View>
          <View style={styles.flex}>
            <Text style={styles.mealName}>{t.healthTitle}</Text>
            <Text style={styles.mutedText}>{t.healthBuildNote}</Text>
          </View>
          <Text style={styles.statusPill}>{healthStatus === "web-unsupported" ? "Web" : "Build"}</Text>
        </View>

        <Text style={styles.cardEyebrow}>{t.health.toUpperCase()}</Text>
        <Text style={styles.modalSub}>{t.healthSub}</Text>
        <ToggleRow testID="toggle-health-sync" title="HealthKit / Health Connect" subtitle="Optional, permission-based" value={permission.health_sync} onToggle={() => updatePermission("health_sync")} />
        <ToggleRow testID="toggle-wearables" title="Supported wearables" subtitle="Optional, permission-based" value={permission.wearables} onToggle={() => updatePermission("wearables")} />
        <ToggleRow testID="toggle-coach-memory" title={t.coachMemory} subtitle={t.coachMemorySub} value={permission.coach_memory} onToggle={() => updatePermission("coach_memory")} />
        <ToggleRow testID="toggle-analytics" title="Anonymous product analytics" subtitle="Help improve NutriMitra" value={permission.analytics} onToggle={() => updatePermission("analytics")} />

        <Text style={[styles.cardEyebrow, { marginTop: 24 }]}>{t.reminders.toUpperCase()}</Text>
        <Text style={styles.modalSub}>{t.remindersSub}</Text>
        <ToggleRow testID="toggle-remind-meals" title={t.remindMeals} subtitle="8:00 · 13:00 · 19:30" value={reminders.meals} onToggle={() => updateReminder("meals")} />
        <ToggleRow testID="toggle-remind-hydration" title={t.remindWater} subtitle="Every 3 hours" value={reminders.hydration} onToggle={() => updateReminder("hydration")} />
        <ToggleRow testID="toggle-remind-movement" title={t.remindMove} subtitle="Every 2 hours" value={reminders.movement} onToggle={() => updateReminder("movement")} />
        <ToggleRow testID="toggle-remind-weekly" title={t.remindWeekly} subtitle="Sundays · 18:00" value={reminders.weekly} onToggle={() => updateReminder("weekly")} />
        {note === "blocked" ? (
          <View style={styles.reasonCard} testID="reminder-blocked">
            <Text style={styles.cardEyebrow}>{t.reminders.toUpperCase()}</Text>
            <Text style={styles.reasonText}>{lang === "te" ? "నోటిఫికేషన్ అనుమతి ఆఫ్‌లో ఉంది. సెట్టింగ్స్‌లో ప్రారంభించండి." : "Notifications are turned off for NutriMitra. Enable them in system settings to receive reminders."}</Text>
            <View style={{ marginTop: 12 }}>
              <Button testID="reminder-open-settings" label={t.openSettings} onPress={() => Linking.openSettings()} secondary />
            </View>
          </View>
        ) : null}
        {note === "denied" ? (
          <View style={styles.reasonCard} testID="reminder-denied">
            <Text style={styles.reasonText}>{lang === "te" ? "రిమైండర్ల కోసం నోటిఫికేషన్ అనుమతి అవసరం." : "Reminders need notification permission. Your preference is saved and will activate once allowed."}</Text>
          </View>
        ) : null}

        <Text style={[styles.cardEyebrow, { marginTop: 24 }]}>{t.language.toUpperCase()}</Text>
        <View style={styles.chipWrap}>
          <Chip label="English" selected={lang === "en"} onPress={() => setLang("en")} />
          <Chip label="తెలుగు" selected={lang === "te"} onPress={() => setLang("te")} />
        </View>

        <Text style={styles.disclaimer}>{t.disclaimer}</Text>
        <Button
          testID="sign-out-button"
          label={t.signOut}
          secondary
          onPress={async () => {
            await signOut();
            router.replace("/");
          }}
        />
        <View style={{ height: Math.max(insets.bottom, 16) }} />
      </ScrollView>
    </View>
  );
}
