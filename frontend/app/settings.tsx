import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post, put } from "@/src/api";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import { LegalLinks } from "@/src/components/legal-links";
import { useAuth } from "@/src/context/auth";
import { getHealthStatus } from "@/src/lib/health";
import { applyReminders, clearReminders, ensureReminderPermissions, remindersSupported } from "@/src/lib/notifications";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { ReminderPrefs } from "@/src/types";

function ToggleRow({ title, subtitle, value, onToggle, testID, disabled = false }: { title: string; subtitle: string; value: boolean; onToggle: () => void; testID: string; disabled?: boolean }) {
  const styles = useStyles();
  return (
    <Pressable testID={testID} accessibilityRole="button" accessibilityLabel={title} accessibilityState={{ disabled }} disabled={disabled} onPress={onToggle} style={[styles.settingRow, disabled && styles.disabled]}>
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
  // The switches show defaults until the saved values arrive; tapping one before then would save the defaults over them.
  const [loaded, setLoaded] = useState({ permissions: false, reminders: false });

  useEffect(() => {
    if (status !== "ready") return;
    api<{ health_sync?: boolean; wearables?: boolean; analytics?: boolean; coach_memory?: boolean }>("/permissions")
      .then((prefs) => {
        setPermission({ health_sync: !!prefs.health_sync, wearables: !!prefs.wearables, analytics: !!prefs.analytics, coach_memory: prefs.coach_memory !== false });
        setLoaded((current) => ({ ...current, permissions: true }));
      })
      .catch(() => undefined);
    api<ReminderPrefs>("/reminders")
      .then((prefs) => {
        setReminders({ meals: !!prefs.meals, hydration: !!prefs.hydration, movement: !!prefs.movement, weekly: !!prefs.weekly });
        setLoaded((current) => ({ ...current, reminders: true }));
      })
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
    return <Redirect href={status === "consent" ? "/consent" : status === "onboarding" ? "/onboarding" : "/welcome"} />;
  }

  const updatePermission = async (key: keyof PermissionPrefs) => {
    if (!loaded.permissions) return;
    const value = !permission[key];
    setPermission({ ...permission, [key]: value });
    // Send only what changed, so a stale copy of the other switches can never overwrite them on the server.
    await post("/permissions", { [key]: value }).catch(() => undefined);
  };

  const updateReminder = async (key: keyof ReminderPrefs) => {
    if (!loaded.reminders) return;
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
          <Text style={styles.eyebrow}>WELLSTRIDE</Text>
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
          <Text style={styles.statusPill}>{healthStatus === "web-unsupported" ? t.statusWeb : t.statusBuild}</Text>
        </View>

        <Text style={styles.cardEyebrow}>{t.health.toUpperCase()}</Text>
        <Text style={styles.modalSub}>{t.healthSub}</Text>
        <ToggleRow testID="toggle-health-sync" disabled={!loaded.permissions} title="HealthKit / Health Connect" subtitle={t.optionalPermission} value={permission.health_sync} onToggle={() => updatePermission("health_sync")} />
        <ToggleRow testID="toggle-wearables" disabled={!loaded.permissions} title={t.wearables} subtitle={t.optionalPermission} value={permission.wearables} onToggle={() => updatePermission("wearables")} />
        <ToggleRow testID="toggle-coach-memory" disabled={!loaded.permissions} title={t.coachMemory} subtitle={t.coachMemorySub} value={permission.coach_memory} onToggle={() => updatePermission("coach_memory")} />
        <ToggleRow testID="toggle-analytics" disabled={!loaded.permissions} title={t.analytics} subtitle={t.analyticsSub} value={permission.analytics} onToggle={() => updatePermission("analytics")} />

        <Text style={[styles.cardEyebrow, { marginTop: 24 }]}>{t.reminders.toUpperCase()}</Text>
        <Text style={styles.modalSub}>{t.remindersSub}</Text>
        <ToggleRow testID="toggle-remind-meals" disabled={!loaded.reminders} title={t.remindMeals} subtitle="8:00 · 13:00 · 19:30" value={reminders.meals} onToggle={() => updateReminder("meals")} />
        <ToggleRow testID="toggle-remind-hydration" disabled={!loaded.reminders} title={t.remindWater} subtitle={t.everyThreeHours} value={reminders.hydration} onToggle={() => updateReminder("hydration")} />
        <ToggleRow testID="toggle-remind-movement" disabled={!loaded.reminders} title={t.remindMove} subtitle={t.everyTwoHours} value={reminders.movement} onToggle={() => updateReminder("movement")} />
        <ToggleRow testID="toggle-remind-weekly" disabled={!loaded.reminders} title={t.remindWeekly} subtitle={t.sundays} value={reminders.weekly} onToggle={() => updateReminder("weekly")} />
        {note === "blocked" ? (
          <View style={styles.reasonCard} testID="reminder-blocked">
            <Text style={styles.cardEyebrow}>{t.reminders.toUpperCase()}</Text>
            <Text style={styles.reasonText}>{t.notifBlocked}</Text>
            <View style={{ marginTop: 12 }}>
              <Button testID="reminder-open-settings" label={t.openSettings} onPress={() => Linking.openSettings()} secondary />
            </View>
          </View>
        ) : null}
        {note === "denied" ? (
          <View style={styles.reasonCard} testID="reminder-denied">
            <Text style={styles.reasonText}>{t.notifDenied}</Text>
          </View>
        ) : null}

        <Text style={[styles.cardEyebrow, { marginTop: 24 }]}>{t.language.toUpperCase()}</Text>
        <View style={styles.chipWrap}>
          <Chip label="English" selected={lang === "en"} onPress={() => setLang("en")} />
          <Chip label="తెలుగు" selected={lang === "te"} onPress={() => setLang("te")} />
        </View>

        <Text style={[styles.cardEyebrow, { marginTop: 24 }]}>{t.legalHeading.toUpperCase()}</Text>
        <LegalLinks />

        <Text style={styles.disclaimer}>{t.disclaimer}</Text>
        <Button
          testID="sign-out-button"
          label={t.signOut}
          secondary
          onPress={async () => {
            // Sign out, then clear the whole navigation stack (not just this modal) before going to the start screen.
            // Replacing only the modal left the old tabs in the stack, and the next sign-in showed a second Today screen.
            await signOut();
            router.dismissAll();
            router.replace("/");
          }}
        />
        <View style={{ height: Math.max(insets.bottom, 16) }} />
      </ScrollView>
    </View>
  );
}
