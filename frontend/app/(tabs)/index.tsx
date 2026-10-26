import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, patch, post } from "@/src/api";
import { Avatar } from "@/src/components/kit";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import {
  CoachCard,
  ShoppingCard,
  WaterCard,
} from "@/src/components/today-cards";
import { useBreakpoint } from "@/src/lib/use-breakpoint";
import { SwapSheet, type SwapTarget } from "@/src/components/swap-sheet";
import { type MealChanges } from "@/src/components/meal-edit-form";
import { TodayMeals } from "@/src/components/today-meals";
import { DeviceActivityCard } from "@/src/components/device-activity-card";
import { TodayProgressCard } from "@/src/components/today-progress-card";
import { TodayNutrientsCard } from "@/src/components/nutrients-card";
import { useToast } from "@/src/components/toast";
import { useAuth } from "@/src/context/auth";
import {
  getHealthStatus,
  HealthSummary,
  syncDeviceHealth,
} from "@/src/lib/health";
import { markPlanMeal, planMealBody } from "@/src/lib/plan";
import { useStyles } from "@/src/styles";
import { layout, makeStyles, radius, useTheme } from "@/src/theme";
import type {
  CheckinResult,
  Dashboard,
  LoggedActivity,
  LoggedMeal,
  Meal,
  Plan,
} from "@/src/types";

const DURATIONS = [10, 20, 30, 45];

const useToday = makeStyles((colors) => ({
  page: {
    width: "100%",
    maxWidth: layout.contentMax,
    alignSelf: "center",
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 40,
    gap: 18,
  },
  pageWide: { paddingHorizontal: 40, paddingTop: 32, gap: 24 },
  head: { flexDirection: "row", alignItems: "center", gap: 12 },
  headWide: { flexWrap: "wrap", gap: 16 },
  hello: { color: colors.muted, fontSize: 13, fontWeight: "600" },
  helloWide: { fontSize: 14 },
  title: {
    color: colors.onSurface,
    fontSize: 28,
    fontWeight: "800",
    letterSpacing: -0.5,
    lineHeight: 34,
  },
  titleWide: { fontSize: 34, lineHeight: 40 },
  headButton: {
    height: 48,
    paddingHorizontal: 20,
    borderRadius: radius.pill,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  week: { flexDirection: "row", justifyContent: "space-between" },
  day: { width: 44, alignItems: "center" },
  dayName: { color: colors.muted, fontSize: 11, fontWeight: "600" },
  dayNum: {
    marginTop: 4,
    width: 36,
    height: 36,
    lineHeight: 36,
    textAlign: "center",
    fontSize: 15,
    fontWeight: "700",
    color: colors.onSurface,
    borderRadius: 18,
    overflow: "hidden",
  },
  dayNumOn: {
    backgroundColor: colors.brandPrimary,
    color: colors.onBrandPrimary,
    fontWeight: "800",
  },
  dayNameOn: { color: colors.brandPrimary, fontWeight: "700" },
  columns: { flexDirection: "row", gap: 24, alignItems: "flex-start" },
  mainColumn: { flex: 1.7, minWidth: 0, gap: 18 },
  sideColumn: { flex: 1, minWidth: 0, gap: 18 },
  moveCard: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: 16,
    boxShadow: colors.shadowCard,
    gap: 12,
  },
  moveHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  moveLabel: { color: colors.muted, fontSize: 13, fontWeight: "700" },
  moveValue: {
    color: colors.onCard,
    fontSize: 26,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  moveUnit: { color: colors.muted, fontSize: 13, fontWeight: "600" },
  verify: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.brandSoft,
    borderRadius: radius.pill,
    paddingLeft: 16,
    paddingRight: 8,
    minHeight: 44,
  },
  verifyMain: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    minHeight: 44,
  },
  verifyText: {
    flex: 1,
    color: colors.brandPrimary,
    fontSize: 14,
    fontWeight: "700",
  },
  verifyClose: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  movePills: { flexDirection: "row", gap: 8 },
  movePill: {
    flex: 1,
    minHeight: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  movePillText: { color: colors.accent, fontSize: 13, fontWeight: "700" },
}));

// The days around today, for orientation only (the dates are not buttons).
function WeekStrip({ lang }: { lang: string }) {
  const w = useToday();
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() + index - 4);
    return date;
  });
  return (
    <View
      style={w.week}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      testID="week-strip"
    >
      {days.map((date, index) => (
        <View key={index} style={w.day}>
          <Text style={[w.dayName, index === 4 && w.dayNameOn]}>
            {date.toLocaleDateString(lang === "te" ? "te-IN" : "en-IN", {
              weekday: "short",
            })}
          </Text>
          <Text style={[w.dayNum, index === 4 && w.dayNumOn]}>
            {date.getDate()}
          </Text>
        </View>
      ))}
    </View>
  );
}

export default function TodayScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, t, lang } = useAuth();
  const w = useToday();
  const { isDesktop } = useBreakpoint();
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
  const [verifyHidden, setVerifyHidden] = useState(false);

  const couldNotLoad = t.couldNotLoad;
  const load = useCallback(async () => {
    try {
      setError("");
      const [nextDashboard, nextPlan, nextHealth, nextCheckin] =
        await Promise.all([
          api<Dashboard>("/dashboard"),
          api<Plan>("/plan"),
          api<HealthSummary>("/health/summary").catch(() => null),
          api<{ result: CheckinResult | null }>("/checkin").catch(() => ({
            result: null,
          })),
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

  const failed = (err: unknown, fallback: string) =>
    toast.show(err instanceof Error ? err.message : fallback, {
      type: "error",
    });

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
    setPlan((current) =>
      current ? markPlanMeal(current, dayIndex, meal, true) : current,
    );
    try {
      const saved = await post<LoggedMeal>("/meals", planMealBody(meal));
      toast.show(t.addMeal, {
        actionLabel: t.undo,
        onAction: () => undoLog(`/meals/${saved.id}`),
      });
      load();
    } catch (err) {
      setPlan((current) =>
        current ? markPlanMeal(current, dayIndex, meal, false) : current,
      );
      failed(err, t.couldNotLogMeal);
    }
  };

  const removeMeal = async (item: LoggedMeal) => {
    setBusy(true);
    try {
      await del(`/meals/${item.id}`);
      const restore = async () => {
        try {
          await post("/meals", {
            meal_type: item.meal_type,
            name: item.name,
            calories: item.calories,
            protein_g: item.protein_g,
            carbs_g: item.carbs_g,
            fat_g: item.fat_g,
            source: item.source,
            portion: item.portion,
          });
        } catch (err) {
          failed(err, t.couldNotUndo);
        }
        await load();
      };
      toast.show(t.removed, {
        type: "info",
        actionLabel: t.undo,
        onAction: restore,
      });
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
          await post("/activities", {
            activity_type: item.activity_type,
            duration_min: item.duration_min,
            distance_km: item.distance_km,
            active_calories: item.active_calories,
            source: item.source,
          });
        } catch (err) {
          failed(err, t.couldNotUndo);
        }
        await load();
      };
      toast.show(t.removed, {
        type: "info",
        actionLabel: t.undo,
        onAction: restore,
      });
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
      const saved = await post<LoggedActivity>("/activities", {
        activity_type: type,
        duration_min: duration,
        source: "manual estimate",
      });
      toast.show(t.addActivity, {
        actionLabel: t.undo,
        onAction: () => undoLog(`/activities/${saved.id}`),
      });
      load();
    } catch (err) {
      failed(err, t.couldNotLogActivity);
    } finally {
      setBusy(false);
    }
  };

  const addWater = async (delta: number) => {
    // Optimistic: the number moves at once; the server's total replaces it.
    setDashboard((current) =>
      current
        ? { ...current, water_ml: Math.max(0, current.water_ml + delta) }
        : current,
    );
    try {
      const saved = await post<{ water_ml: number }>("/water", {
        delta_ml: delta,
      });
      setDashboard((current) =>
        current ? { ...current, water_ml: saved.water_ml } : current,
      );
    } catch (err) {
      failed(err, t.pleaseTryAgain);
      await load();
    }
  };

  const swapMeal = async (meal: Meal) => {
    if (!swapTarget) return;
    setSwapping(true);
    try {
      const next = await post<Plan>("/plan/swap", {
        day: swapTarget.day,
        type: swapTarget.type,
        name: meal.name,
      });
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
    ({
      nothing_logged: t.checkinNothing,
      low_protein: t.checkinLowProtein,
      on_track: t.checkinOnTrack,
      low_energy: t.checkinLowEnergy,
      above: t.checkinAbove,
    })[result.status];

  const syncDevice = async () => {
    setSyncing(true);
    const result = await syncDeviceHealth();
    toast.show(result ? t.syncDone : t.syncUnavailable, {
      type: result ? "success" : "info",
    });
    await load();
    setSyncing(false);
  };

  // The evening check-in shows from 5 pm (or once it is done).
  const checkinVisible =
    !!plan &&
    (new Date().getHours() >= 17 ||
      (checkin !== null && checkin.status !== "nothing_logged"));
  const todayPlan = plan?.days?.[plan.today_index ?? 0];
  const meals = todayPlan?.meals || [];
  const deviceReady = getHealthStatus() === "ready";
  const sleepHours = health
    ? Math.round((health.sleep_minutes / 60) * 10) / 10
    : 0;

  const hello = (user?.name || t.friend).split(" ")[0];
  const dateText = new Date().toLocaleDateString(
    lang === "te" ? "te-IN" : "en-IN",
    { weekday: "long", day: "numeric", month: "long" },
  );
  const dateLine = isDesktop
    ? t.todayDateLine
        .replace("{date}", dateText)
        .replace("{hello}", t.hello)
        .replace("{name}", hello)
    : `${t.hello}, ${hello}`;

  const progress = (
    <>
      <TodayProgressCard dashboard={dashboard} t={t} />
      <TodayNutrientsCard nutrients={dashboard?.nutrients} />
    </>
  );
  const mealsBlock = (
    <>
      <View style={styles.sectionHeader}>
        <View style={styles.flex}>
          <Text style={styles.sectionTitleSmall}>{t.meals}</Text>
          <Text style={styles.mutedText}>
            {todayPlan?.focus || t.defaultFocus}
          </Text>
        </View>
        <Pressable
          testID="log-food-button"
          accessibilityRole="button"
          onPress={() => router.push("/log-food")}
        >
          <Text style={styles.linkText}>{t.logFood}</Text>
        </Pressable>
      </View>
      <TodayMeals
        wide={isDesktop}
        logged={dashboard?.meals || []}
        suggestions={meals}
        busy={busy}
        editingId={editingId}
        setEditingId={setEditingId}
        onSave={saveMeal}
        onRemove={removeMeal}
        onAdd={(slot, mode) =>
          router.push({
            pathname: "/log-food",
            params: mode ? { slot, mode } : { slot },
          })
        }
        onLogSuggestion={logMeal}
        onSwap={(meal) =>
          setSwapTarget({ day: plan?.today_index ?? 0, type: meal.type })
        }
      />
    </>
  );
  const movement = (
    <View style={w.moveCard} testID="movement-card">
      <View style={w.moveHead}>
        <AppIcon name="activity" color={colors.accent} size={18} />
        <Text style={w.moveLabel}>{t.movement}</Text>
      </View>
      <Text style={w.moveValue}>
        {dashboard?.activity_minutes || 0}{" "}
        <Text style={w.moveUnit}>{t.minutes}</Text>
        <Text style={w.moveUnit}>
          {" "}
          · ~{dashboard?.active_calories || 0} kcal
        </Text>
      </Text>
      <View style={styles.durationRow} testID="activity-duration">
        {DURATIONS.map((minutes) => (
          <Chip
            key={minutes}
            label={`${minutes} ${t.minutes}`}
            selected={duration === minutes}
            onPress={() => setDuration(minutes)}
          />
        ))}
      </View>
      <View style={w.movePills}>
        <Pressable
          testID="log-walk-button"
          accessibilityRole="button"
          disabled={busy}
          onPress={() => addActivity("Walking", duration)}
          style={({ pressed }) => [
            w.movePill,
            pressed && styles.pressed,
            busy && styles.disabled,
          ]}
        >
          <Text style={w.movePillText}>
            {t.walkWord} · {duration} {t.minutes}
          </Text>
        </Pressable>
        <Pressable
          testID="log-strength-button"
          accessibilityRole="button"
          disabled={busy}
          onPress={() => addActivity("Home strength", duration)}
          style={({ pressed }) => [
            w.movePill,
            pressed && styles.pressed,
            busy && styles.disabled,
          ]}
        >
          <Text style={w.movePillText}>
            {t.strengthWord} · {duration} {t.minutes}
          </Text>
        </Pressable>
      </View>
      <Text style={styles.mutedText}>{t.activityHint}</Text>
      {(dashboard?.activities?.length || 0) > 0 ? (
        <View style={styles.reasonCard} testID="logged-activities">
          <Text style={styles.cardEyebrow}>{t.loggedToday.toUpperCase()}</Text>
          {dashboard?.activities?.map((item) => (
            <View
              key={item.id}
              style={styles.logRow}
              testID={`logged-activity-${item.id}`}
            >
              <View style={styles.flex}>
                <Text style={styles.mealName}>{item.activity_type}</Text>
                <Text style={styles.mealMeta}>
                  {item.duration_min} {t.minutes} · {item.active_calories} kcal
                </Text>
              </View>
              <Pressable
                testID={`remove-activity-${item.id}`}
                accessibilityRole="button"
                accessibilityLabel={`${t.remove} ${item.activity_type}`}
                disabled={busy}
                onPress={() => removeActivity(item)}
                style={({ pressed }) => [
                  styles.removeButton,
                  pressed && styles.pressed,
                  busy && styles.disabled,
                ]}
              >
                <Text style={styles.linkText}>{t.remove}</Text>
              </Pressable>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
  const water = <WaterCard dashboard={dashboard} t={t} onAdd={addWater} />;
  const coach = (
    <CoachCard
      dashboard={dashboard}
      t={t}
      onEatNow={() => router.push("/eat-now")}
      onOpen={(prompt) =>
        router.push({
          pathname: "/(tabs)/coach",
          params: prompt ? { prompt } : {},
        })
      }
    />
  );
  const shopping = (
    <ShoppingCard
      toBuy={plan?.also_buy || []}
      lang={lang}
      t={t}
      onOpen={() => router.push("/shopping-list")}
    />
  );
  const extras = (
    <>
      {checkinVisible ? (
        <View style={styles.reasonCard} testID="checkin-card">
          <Text style={styles.cardEyebrow}>{t.checkinTitle.toUpperCase()}</Text>
          {checkin && checkin.status !== "nothing_logged" ? (
            <>
              <Text style={styles.reasonText} testID="checkin-message">
                {checkinMessage(checkin)}
              </Text>
              <Text style={styles.mutedText} testID="checkin-numbers">
                {checkin.calories} / {checkin.target_calories} kcal ·{" "}
                {checkin.protein_g} / {checkin.target_protein_g} g{" "}
                {t.proteinWord}
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.reasonText} testID="checkin-message">
                {checkin ? checkinMessage(checkin) : t.checkinSub}
              </Text>
              <View style={{ marginTop: 12 }}>
                <Button
                  testID="checkin-button"
                  label={checkingIn ? "..." : t.checkinButton}
                  onPress={doCheckin}
                  disabled={checkingIn}
                />
              </View>
            </>
          )}
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
      {!deviceReady && health?.connected ? (
        <Text style={styles.mutedText}>{t.syncUnavailable}</Text>
      ) : null}
      <View style={styles.reasonCard}>
        <Text style={styles.cardEyebrow}>{t.nutrition.toUpperCase()}</Text>
        <Text style={styles.reasonText}>
          {plan?.reasoning || t.planReasoningFallback}
        </Text>
      </View>
    </>
  );

  return (
    <View
      style={[styles.root, { paddingTop: insets.top }]}
      testID="today-screen"
    >
      {!dashboard && !error ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brandPrimary} />
          <Text style={styles.mutedText}>{t.loadingToday}</Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={[w.page, isDesktop && w.pageWide]}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={refresh}
              tintColor={colors.brandPrimary}
            />
          }
        >
          <View style={[w.head, isDesktop && w.headWide]}>
            {!isDesktop ? (
              <Avatar name={user?.name || t.friend} size={44} />
            ) : null}
            <View style={[styles.flex, isDesktop && { minWidth: 240 }]}>
              <Text style={[w.hello, isDesktop && w.helloWide]}>
                {dateLine}
              </Text>
              <Text
                style={[w.title, isDesktop && w.titleWide]}
                accessibilityRole="header"
              >
                {t.today}
              </Text>
            </View>
            {isDesktop ? (
              <>
                <Pressable
                  testID="header-snap-meal"
                  accessibilityRole="button"
                  accessibilityLabel={t.snapMealShort}
                  onPress={() =>
                    router.push({
                      pathname: "/log-food",
                      params: { mode: "photo" },
                    })
                  }
                  style={({ pressed }) => [
                    w.headButton,
                    { borderWidth: 1.5, borderColor: colors.brandPrimary },
                    pressed && styles.pressed,
                  ]}
                >
                  <AppIcon
                    name="camera"
                    color={colors.brandPrimary}
                    size={18}
                  />
                  <Text style={styles.linkText}>{t.snapMealShort}</Text>
                </Pressable>
                <Pressable
                  testID="header-add-food"
                  accessibilityRole="button"
                  accessibilityLabel={t.addFood}
                  onPress={() => router.push("/log-food")}
                  style={({ pressed }) => [
                    w.headButton,
                    { backgroundColor: colors.brandPrimary },
                    pressed && styles.pressed,
                  ]}
                >
                  <AppIcon name="add" color={colors.onBrandPrimary} size={18} />
                  <Text
                    style={[styles.linkText, { color: colors.onBrandPrimary }]}
                  >
                    {t.addFood}
                  </Text>
                </Pressable>
              </>
            ) : (
              <Pressable
                testID="open-settings-button"
                accessibilityRole="button"
                accessibilityLabel={t.settings}
                onPress={() => router.push("/settings")}
                style={styles.iconButton}
              >
                <AppIcon
                  name="gearshape.fill"
                  color={colors.onSurface}
                  size={21}
                />
              </Pressable>
            )}
          </View>
          {!isDesktop ? <WeekStrip lang={lang} /> : null}
          {error ? (
            <View style={styles.reasonCard} testID="today-error">
              <Text style={styles.cardEyebrow}>
                {t.connection.toUpperCase()}
              </Text>
              <Text style={styles.reasonText}>{error}</Text>
            </View>
          ) : null}
          {user && user.email_verified === false && !verifyHidden ? (
            <View style={w.verify} testID="verify-banner">
              <Pressable
                testID="verify-banner-open"
                accessibilityRole="button"
                accessibilityLabel={t.verifyBannerTitle}
                onPress={() => router.push("/verify-email")}
                style={w.verifyMain}
              >
                <AppIcon name="mail" color={colors.brandPrimary} size={18} />
                <Text style={w.verifyText} numberOfLines={2}>
                  {t.verifyBannerTitle}
                </Text>
                <AppIcon
                  name="chevron.right"
                  color={colors.brandPrimary}
                  size={16}
                />
              </Pressable>
              <Pressable
                testID="verify-banner-dismiss"
                accessibilityRole="button"
                accessibilityLabel={t.verifyDismiss}
                onPress={() => setVerifyHidden(true)}
                hitSlop={8}
                style={w.verifyClose}
              >
                <AppIcon name="close" color={colors.muted} size={16} />
              </Pressable>
            </View>
          ) : null}
          {isDesktop ? (
            <View style={w.columns}>
              <View style={w.mainColumn}>
                {progress}
                {mealsBlock}
              </View>
              <View style={w.sideColumn}>
                {water}
                {movement}
                {coach}
                {shopping}
                {extras}
              </View>
            </View>
          ) : (
            <>
              {progress}
              {mealsBlock}
              {water}
              {movement}
              {coach}
              {shopping}
              {extras}
            </>
          )}
          <Text style={styles.disclaimer}>{t.disclaimer}</Text>
        </ScrollView>
      )}
      <SwapSheet
        target={swapTarget}
        busy={swapping}
        onChoose={swapMeal}
        onClose={() => setSwapTarget(null)}
      />
    </View>
  );
}
