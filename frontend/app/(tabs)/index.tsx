import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, patch, post } from "@/src/api";
import { AppIcon, Chip, MealCard } from "@/src/components/ui";
import { MealEditForm, type MealChanges } from "@/src/components/meal-edit-form";
import { DeviceActivityCard } from "@/src/components/device-activity-card";
import { TodayProgressCard } from "@/src/components/today-progress-card";
import { useAuth } from "@/src/context/auth";
import { getHealthStatus, HealthSummary, syncDeviceHealth } from "@/src/lib/health";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import { mealTypeLabel } from "@/src/i18n";
import type { Dashboard, Meal, Plan } from "@/src/types";

const DURATIONS = [10, 20, 30, 45];

export default function TodayScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, t } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [duration, setDuration] = useState(20);
  const [editingId, setEditingId] = useState<string | null>(null);

  const couldNotLoad = t.couldNotLoad;
  const load = useCallback(async () => {
    try {
      setError("");
      const [nextDashboard, nextPlan, nextHealth] = await Promise.all([
        api<Dashboard>("/dashboard"),
        api<Plan>("/plan"),
        api<HealthSummary>("/health/summary").catch(() => null),
      ]);
      setDashboard(nextDashboard);
      setPlan(nextPlan);
      setHealth(nextHealth);
    } catch (err) {
      setError(err instanceof Error ? err.message : couldNotLoad);
    }
  }, [couldNotLoad]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const refresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const logMeal = async (meal: Meal) => {
    try {
      await post("/meals", { meal_type: meal.type, name: meal.name, calories: meal.calories, protein_g: meal.protein_g, carbs_g: meal.carbs_g, fat_g: meal.fat_g, source: "plan" });
      setMessage(t.addMeal);
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t.couldNotLogMeal);
    }
  };

  const removeEntry = async (path: string) => {
    setBusy(true);
    try {
      await del(path);
      setMessage(t.removed);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t.couldNotRemove);
    } finally {
      setBusy(false);
    }
  };

  const saveMeal = async (id: string, changes: MealChanges) => {
    setBusy(true);
    try {
      await patch(`/meals/${id}`, changes);
      setEditingId(null);
      setMessage(t.mealUpdated);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t.couldNotUpdateMeal);
    } finally {
      setBusy(false);
    }
  };

  const addActivity = async (type: string, duration: number) => {
    setBusy(true);
    try {
      // Calories (and walking distance) are estimated by the server from duration and body weight.
      await post("/activities", { activity_type: type, duration_min: duration, source: "manual estimate" });
      setMessage(t.addActivity);
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t.couldNotLogActivity);
    } finally {
      setBusy(false);
    }
  };

  const syncDevice = async () => {
    setSyncing(true);
    const result = await syncDeviceHealth();
    setMessage(result ? t.syncDone : t.syncUnavailable);
    await load();
    setSyncing(false);
  };

  const todayPlan = plan?.days?.[plan.today_index ?? 0];
  const meals = todayPlan?.meals || [];
  const deviceReady = getHealthStatus() === "ready";
  const sleepHours = health ? Math.round((health.sleep_minutes / 60) * 10) / 10 : 0;

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="today-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>
            {t.hello.toUpperCase()}, {(user?.name || t.friend).split(" ")[0].toUpperCase()}
          </Text>
          <Text style={styles.headerTitle}>{t.today}</Text>
        </View>
        <Pressable testID="open-settings-button" accessibilityRole="button" accessibilityLabel={t.settings} onPress={() => router.push("/settings")} style={styles.iconButton}>
          <AppIcon name="gearshape.fill" color={colors.onSurface} size={21} />
        </Pressable>
      </View>
      {!dashboard && !error ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brandPrimary} />
          <Text style={styles.mutedText}>{t.loadingToday}</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.brandPrimary} />}>
          {error ? (
            <View style={styles.reasonCard} testID="today-error">
              <Text style={styles.cardEyebrow}>{t.connection.toUpperCase()}</Text>
              <Text style={styles.reasonText}>{error}</Text>
            </View>
          ) : null}
          {user && user.email_verified === false ? (
            <Pressable testID="verify-banner" accessibilityRole="button" onPress={() => router.push("/verify-email")} style={({ pressed }) => [styles.eatBanner, { marginBottom: 12 }, pressed && styles.pressed]}>
              <View style={styles.flex}>
                <Text style={styles.bannerTitle}>{t.verifyBannerTitle}</Text>
                <Text style={styles.bannerSub}>{t.verifyBannerSub}</Text>
              </View>
              <AppIcon name="chevron.right" color={colors.onSurface} size={18} />
            </Pressable>
          ) : null}
          <TodayProgressCard dashboard={dashboard} t={t} styles={styles} />
          <Pressable testID="eat-now-button" accessibilityRole="button" onPress={() => router.push("/eat-now")} style={({ pressed }) => [styles.eatBanner, pressed && styles.pressed]}>
            <View style={styles.bannerIcon}>
              <AppIcon name="sparkles" color={colors.onBrandPrimary} size={23} />
            </View>
            <View style={styles.flex}>
              <Text style={styles.bannerTitle}>{t.eatNow}</Text>
              <Text style={styles.bannerSub}>{t.eatSub}</Text>
            </View>
            <AppIcon name="chevron.right" color={colors.onSurface} size={18} />
          </Pressable>
          <View style={styles.sectionHeader}>
            <View style={styles.flex}>
              <Text style={styles.sectionTitleSmall}>{t.meals}</Text>
              <Text style={styles.mutedText}>{todayPlan?.focus || t.defaultFocus}</Text>
            </View>
            <Pressable testID="log-food-photo-button" accessibilityRole="button" onPress={() => router.push("/log-food")}>
              <Text style={styles.linkText}>{t.photo}</Text>
            </Pressable>
          </View>
          {meals.map((meal) => (
            <MealCard key={`${meal.type}-${meal.name}`} meal={meal} onLog={() => logMeal(meal)} />
          ))}
          {(dashboard?.meals?.length || 0) > 0 ? (
            <View style={styles.reasonCard} testID="logged-meals">
              <Text style={styles.cardEyebrow}>{t.loggedToday.toUpperCase()}</Text>
              <Text style={styles.reasonText}>
                {dashboard?.meals?.length} {t.mealsWord} · {dashboard?.calories || 0} kcal {t.soFar}
              </Text>
              {dashboard?.meals?.map((item) =>
                editingId === item.id ? (
                  <MealEditForm key={item.id} meal={item} t={t} busy={busy} onSave={(changes) => saveMeal(item.id, changes)} onCancel={() => setEditingId(null)} />
                ) : (
                  <View key={item.id} style={styles.logRow} testID={`logged-meal-${item.id}`}>
                    <View style={styles.flex}>
                      <Text style={styles.mealName}>{item.name}</Text>
                      <Text style={styles.mealMeta}>
                        {mealTypeLabel(t, item.meal_type)} · {item.calories} kcal · {item.protein_g}g {t.proteinWord}
                      </Text>
                    </View>
                    <View style={styles.rowActions}>
                      <Pressable testID={`edit-meal-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.edit} ${item.name}`} disabled={busy} onPress={() => setEditingId(item.id)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                        <Text style={styles.linkText}>{t.edit}</Text>
                      </Pressable>
                      <Pressable testID={`remove-meal-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.remove} ${item.name}`} disabled={busy} onPress={() => removeEntry(`/meals/${item.id}`)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                        <Text style={styles.linkText}>{t.remove}</Text>
                      </Pressable>
                    </View>
                  </View>
                ),
              )}
            </View>
          ) : null}
          <View style={styles.sectionHeader}>
            <View style={styles.flex}>
              <Text style={styles.sectionTitleSmall}>{t.movement}</Text>
              <Text style={styles.mutedText}>
                {dashboard?.active_calories || 0} {t.activeKcalNote}
              </Text>
            </View>
          </View>
          <View style={styles.activityHero}>
            <View style={styles.bigRing}>
              <Text style={styles.bigRingValue}>{dashboard?.activities?.length ? "On" : "0"}</Text>
              <Text style={styles.bigRingCaption}>{dashboard?.activities?.length ? t.ringMoving : t.ringSessions}</Text>
            </View>
            <View style={styles.flex}>
              <Text style={styles.mealName}>{t.startWalk}</Text>
              <Text style={styles.reasonText}>{t.activityHint}</Text>
            </View>
          </View>
          <View style={styles.durationRow} testID="activity-duration">
            {DURATIONS.map((minutes) => (
              <Chip key={minutes} label={`${minutes} ${t.minutes}`} selected={duration === minutes} onPress={() => setDuration(minutes)} />
            ))}
          </View>
          <View style={styles.row}>
            <View style={styles.half}>
              <Pressable testID="log-walk-button" accessibilityRole="button" disabled={busy} onPress={() => addActivity("Walking", duration)} style={({ pressed }) => [styles.button, pressed && styles.pressed, busy && styles.disabled]}>
                <Text style={styles.buttonText}>
                  {t.walkWord} · {duration} {t.minutes}
                </Text>
              </Pressable>
            </View>
            <View style={styles.half}>
              <Pressable testID="log-strength-button" accessibilityRole="button" disabled={busy} onPress={() => addActivity("Home strength", duration)} style={({ pressed }) => [styles.button, styles.buttonSecondary, pressed && styles.pressed, busy && styles.disabled]}>
                <Text style={styles.buttonSecondaryText}>
                  {t.strengthWord} · {duration} {t.minutes}
                </Text>
              </Pressable>
            </View>
          </View>
          {(dashboard?.activities?.length || 0) > 0 ? (
            <View style={styles.reasonCard} testID="logged-activities">
              <Text style={styles.cardEyebrow}>{t.loggedToday.toUpperCase()}</Text>
              {dashboard?.activities?.map((item) => (
                <View key={item.id} style={styles.logRow} testID={`logged-activity-${item.id}`}>
                  <View style={styles.flex}>
                    <Text style={styles.mealName}>{item.activity_type}</Text>
                    <Text style={styles.mealMeta}>
                      {item.duration_min} {t.minutes} · {item.active_calories} kcal
                    </Text>
                  </View>
                  <Pressable testID={`remove-activity-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.remove} ${item.activity_type}`} disabled={busy} onPress={() => removeEntry(`/activities/${item.id}`)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                    <Text style={styles.linkText}>{t.remove}</Text>
                  </Pressable>
                </View>
              ))}
            </View>
          ) : null}
          <View style={styles.sectionHeader}>
            <View style={styles.flex}>
              <Text style={styles.sectionTitleSmall}>{t.deviceActivity}</Text>
              <Text style={styles.mutedText}>Apple Health · Health Connect</Text>
            </View>
          </View>
          <DeviceActivityCard
            health={health}
            sleepHours={sleepHours}
            t={t}
            styles={styles}
            colors={colors}
            syncing={syncing}
            onSync={syncDevice}
            onOpenSettings={() => router.push("/settings")}
          />
          {!deviceReady && health?.connected ? <Text style={styles.mutedText}>{t.syncUnavailable}</Text> : null}
          <View style={styles.reasonCard}>
            <Text style={styles.cardEyebrow}>{t.nutrition.toUpperCase()}</Text>
            <Text style={styles.reasonText}>{plan?.reasoning || t.planReasoningFallback}</Text>
          </View>
          <Text style={styles.disclaimer}>{t.disclaimer}</Text>
        </ScrollView>
      )}
      {message ? (
        <Pressable testID="today-toast" onPress={() => setMessage("")} style={styles.toast}>
          <Text style={styles.toastText}>{message}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
