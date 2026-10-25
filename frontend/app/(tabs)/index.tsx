import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, patch, post } from "@/src/api";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import { SwapSheet, type SwapTarget } from "@/src/components/swap-sheet";
import { type MealChanges } from "@/src/components/meal-edit-form";
import { TodayMeals } from "@/src/components/today-meals";
import { DeviceActivityCard } from "@/src/components/device-activity-card";
import { TodayProgressCard } from "@/src/components/today-progress-card";
import { useToast } from "@/src/components/toast";
import { useAuth } from "@/src/context/auth";
import { getHealthStatus, HealthSummary, syncDeviceHealth } from "@/src/lib/health";
import { markPlanMeal, planMealBody } from "@/src/lib/plan";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { CheckinResult, Dashboard, LoggedActivity, LoggedMeal, Meal, Plan } from "@/src/types";

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
  const toast = useToast();
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [duration, setDuration] = useState(20);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [swapTarget, setSwapTarget] = useState<SwapTarget | null>(null);
  const [swapping, setSwapping] = useState(false);
  const [checkin, setCheckin] = useState<CheckinResult | null>(null);
  const [checkingIn, setCheckingIn] = useState(false);

  const couldNotLoad = t.couldNotLoad;
  const load = useCallback(async () => {
    try {
      setError("");
      const [nextDashboard, nextPlan, nextHealth, nextCheckin] = await Promise.all([
        api<Dashboard>("/dashboard"),
        api<Plan>("/plan"),
        api<HealthSummary>("/health/summary").catch(() => null),
        api<{ result: CheckinResult | null }>("/checkin").catch(() => ({ result: null })),
      ]);
      setDashboard(nextDashboard);
      setPlan(nextPlan);
      setHealth(nextHealth);
      setCheckin(nextCheckin.result);
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

  const failed = (err: unknown, fallback: string) => toast.show(err instanceof Error ? err.message : fallback, { type: "error" });

  const undoLog = async (path: string) => {
    try {
      await del(path);
      toast.show(t.undone, { type: "info" });
    } catch (err) {
      failed(err, t.couldNotUndo);
    }
    await load();
  };

  const logMeal = async (meal: Meal) => {
    // Optimistic: the "+" becomes the check at once; the server's answer confirms it or rolls it back.
    const dayIndex = plan?.today_index ?? 0;
    setPlan((current) => (current ? markPlanMeal(current, dayIndex, meal, true) : current));
    try {
      const saved = await post<LoggedMeal>("/meals", planMealBody(meal));
      toast.show(t.addMeal, { actionLabel: t.undo, onAction: () => undoLog(`/meals/${saved.id}`) });
      load();
    } catch (err) {
      setPlan((current) => (current ? markPlanMeal(current, dayIndex, meal, false) : current));
      failed(err, t.couldNotLogMeal);
    }
  };

  const removeMeal = async (item: LoggedMeal) => {
    setBusy(true);
    try {
      await del(`/meals/${item.id}`);
      const restore = async () => {
        try {
          await post("/meals", { meal_type: item.meal_type, name: item.name, calories: item.calories, protein_g: item.protein_g, carbs_g: item.carbs_g, fat_g: item.fat_g, source: item.source, portion: item.portion });
        } catch (err) {
          failed(err, t.couldNotUndo);
        }
        await load();
      };
      toast.show(t.removed, { type: "info", actionLabel: t.undo, onAction: restore });
      await load();
    } catch (err) {
      failed(err, t.couldNotRemove);
    } finally {
      setBusy(false);
    }
  };

  const removeActivity = async (item: LoggedActivity) => {
    setBusy(true);
    try {
      await del(`/activities/${item.id}`);
      const restore = async () => {
        try {
          await post("/activities", { activity_type: item.activity_type, duration_min: item.duration_min, distance_km: item.distance_km, active_calories: item.active_calories, source: item.source });
        } catch (err) {
          failed(err, t.couldNotUndo);
        }
        await load();
      };
      toast.show(t.removed, { type: "info", actionLabel: t.undo, onAction: restore });
      await load();
    } catch (err) {
      failed(err, t.couldNotRemove);
    } finally {
      setBusy(false);
    }
  };

  const saveMeal = async (id: string, changes: MealChanges) => {
    setBusy(true);
    try {
      await patch(`/meals/${id}`, changes);
      setEditingId(null);
      toast.show(t.mealUpdated);
      await load();
    } catch (err) {
      failed(err, t.couldNotUpdateMeal);
    } finally {
      setBusy(false);
    }
  };

  const addActivity = async (type: string, duration: number) => {
    setBusy(true);
    try {
      // Calories (and walking distance) are estimated by the server from duration and body weight.
      const saved = await post<LoggedActivity>("/activities", { activity_type: type, duration_min: duration, source: "manual estimate" });
      toast.show(t.addActivity, { actionLabel: t.undo, onAction: () => undoLog(`/activities/${saved.id}`) });
      load();
    } catch (err) {
      failed(err, t.couldNotLogActivity);
    } finally {
      setBusy(false);
    }
  };

  const swapMeal = async (meal: Meal) => {
    if (!swapTarget) return;
    setSwapping(true);
    try {
      const next = await post<Plan>("/plan/swap", { day: swapTarget.day, type: swapTarget.type, name: meal.name });
      setPlan(next);
      setSwapTarget(null);
      toast.show(t.swapped);
    } catch (err) {
      failed(err, t.couldNotSwap);
    } finally {
      setSwapping(false);
    }
  };

  const doCheckin = async () => {
    setCheckingIn(true);
    try {
      const answer = await post<{ result: CheckinResult }>("/checkin", {});
      setCheckin(answer.result);
      if (answer.result.adjusted_day !== null) {
        toast.show(t.checkinTomorrow, { type: "info" });
        await load();
      }
    } catch (err) {
      failed(err, t.checkinFailed);
    } finally {
      setCheckingIn(false);
    }
  };

  const checkinMessage = (result: CheckinResult) =>
    ({ nothing_logged: t.checkinNothing, low_protein: t.checkinLowProtein, on_track: t.checkinOnTrack, low_energy: t.checkinLowEnergy, above: t.checkinAbove })[result.status];

  const syncDevice = async () => {
    setSyncing(true);
    const result = await syncDeviceHealth();
    toast.show(result ? t.syncDone : t.syncUnavailable, { type: result ? "success" : "info" });
    await load();
    setSyncing(false);
  };

  // The evening check-in shows from 5 pm (or once it is done).
  const checkinVisible = !!plan && (new Date().getHours() >= 17 || (checkin !== null && checkin.status !== "nothing_logged"));
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
          <TodayProgressCard dashboard={dashboard} t={t} />
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
            <Pressable testID="log-food-button" accessibilityRole="button" onPress={() => router.push("/log-food")}>
              <Text style={styles.linkText}>{t.logFood}</Text>
            </Pressable>
          </View>
          <TodayMeals
            logged={dashboard?.meals || []}
            suggestions={meals}
            busy={busy}
            editingId={editingId}
            setEditingId={setEditingId}
            onSave={saveMeal}
            onRemove={removeMeal}
            onAdd={(slot, mode) => router.push({ pathname: "/log-food", params: mode ? { slot, mode } : { slot } })}
            onLogSuggestion={logMeal}
            onSwap={(meal) => setSwapTarget({ day: plan?.today_index ?? 0, type: meal.type })}
          />
          {checkinVisible ? (
            <View style={styles.reasonCard} testID="checkin-card">
              <Text style={styles.cardEyebrow}>{t.checkinTitle.toUpperCase()}</Text>
              {checkin && checkin.status !== "nothing_logged" ? (
                <>
                  <Text style={styles.reasonText} testID="checkin-message">
                    {checkinMessage(checkin)}
                  </Text>
                  <Text style={styles.mutedText} testID="checkin-numbers">
                    {checkin.calories} / {checkin.target_calories} kcal · {checkin.protein_g} / {checkin.target_protein_g} g {t.proteinWord}
                  </Text>
                </>
              ) : (
                <>
                  <Text style={styles.reasonText} testID="checkin-message">
                    {checkin ? checkinMessage(checkin) : t.checkinSub}
                  </Text>
                  <View style={{ marginTop: 12 }}>
                    <Button testID="checkin-button" label={checkingIn ? "..." : t.checkinButton} onPress={doCheckin} disabled={checkingIn} />
                  </View>
                </>
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
                  <Pressable testID={`remove-activity-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.remove} ${item.activity_type}`} disabled={busy} onPress={() => removeActivity(item)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
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
      <SwapSheet target={swapTarget} busy={swapping} onChoose={swapMeal} onClose={() => setSwapTarget(null)} />
    </View>
  );
}
