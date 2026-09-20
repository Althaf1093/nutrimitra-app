import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post } from "@/src/api";
import { AppIcon, MealCard } from "@/src/components/ui";
import { DeviceActivityCard } from "@/src/components/device-activity-card";
import { ReadinessCard } from "@/src/components/readiness-card";
import { useAuth } from "@/src/context/auth";
import { getHealthStatus, HealthSummary, syncDeviceHealth } from "@/src/lib/health";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Dashboard, Meal, Plan } from "@/src/types";

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
      setError(err instanceof Error ? err.message : "Could not load your wellness data");
    }
  }, []);

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
      setMessage(err instanceof Error ? err.message : "Could not log meal");
    }
  };

  const addActivity = async (type: string, duration: number) => {
    setBusy(true);
    try {
      await post("/activities", { activity_type: type, duration_min: duration, distance_km: type === "Walking" ? 2.1 : 0, active_calories: type === "Walking" ? 120 : 80, source: "manual estimate" });
      setMessage(t.addActivity);
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not log activity");
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

  const todayPlan = plan?.days?.[0];
  const meals = todayPlan?.meals || [];
  const deviceReady = getHealthStatus() === "ready";
  const sleepHours = health ? Math.round((health.sleep_minutes / 60) * 10) / 10 : 0;

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="today-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>
            {t.hello.toUpperCase()}, {(user?.name || "Friend").split(" ")[0].toUpperCase()}
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
          <Text style={styles.mutedText}>Loading today’s wellness insights…</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.brandPrimary} />}>
          {error ? (
            <View style={styles.reasonCard} testID="today-error">
              <Text style={styles.cardEyebrow}>CONNECTION</Text>
              <Text style={styles.reasonText}>{error}</Text>
            </View>
          ) : null}
          <ReadinessCard dashboard={dashboard} t={t} styles={styles} />
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
              <Text style={styles.mutedText}>{todayPlan?.focus || "Protein + fibre balance"}</Text>
            </View>
            <Pressable testID="log-food-photo-button" accessibilityRole="button" onPress={() => router.push("/log-food")}>
              <Text style={styles.linkText}>{t.photo}</Text>
            </Pressable>
          </View>
          {meals.map((meal) => (
            <MealCard key={`${meal.type}-${meal.name}`} meal={meal} onLog={() => logMeal(meal)} />
          ))}
          {(dashboard?.meals?.length || 0) > 0 ? (
            <View style={styles.reasonCard}>
              <Text style={styles.cardEyebrow}>LOGGED TODAY</Text>
              <Text style={styles.reasonText}>
                {dashboard?.meals?.length} meal(s) · {dashboard?.calories || 0} kcal so far
              </Text>
            </View>
          ) : null}
          <View style={styles.sectionHeader}>
            <View style={styles.flex}>
              <Text style={styles.sectionTitleSmall}>{t.movement}</Text>
              <Text style={styles.mutedText}>
                {dashboard?.active_calories || 0} active kcal · {t.estimate.toLowerCase()}s labelled
              </Text>
            </View>
          </View>
          <View style={styles.activityHero}>
            <View style={styles.bigRing}>
              <Text style={styles.bigRingValue}>{dashboard?.activities?.length ? "On" : "0"}</Text>
              <Text style={styles.bigRingCaption}>{dashboard?.activities?.length ? "moving" : "sessions"}</Text>
            </View>
            <View style={styles.flex}>
              <Text style={styles.mealName}>{t.startWalk}</Text>
              <Text style={styles.reasonText}>A 20-minute comfortable walk is a useful place to begin. Listen to your body.</Text>
            </View>
          </View>
          <View style={styles.row}>
            <View style={styles.half}>
              <Pressable testID="log-walk-button" accessibilityRole="button" disabled={busy} onPress={() => addActivity("Walking", 20)} style={({ pressed }) => [styles.button, pressed && styles.pressed, busy && styles.disabled]}>
                <Text style={styles.buttonText}>Walk · 20 {t.minutes}</Text>
              </Pressable>
            </View>
            <View style={styles.half}>
              <Pressable testID="log-strength-button" accessibilityRole="button" disabled={busy} onPress={() => addActivity("Home strength", 15)} style={({ pressed }) => [styles.button, styles.buttonSecondary, pressed && styles.pressed, busy && styles.disabled]}>
                <Text style={styles.buttonSecondaryText}>Strength · 15 {t.minutes}</Text>
              </Pressable>
            </View>
          </View>
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
            <Text style={styles.reasonText}>{plan?.reasoning || "Your plate is built around familiar flavours, satisfying protein and fibre-rich ingredients for steadier energy—without removing joy from food."}</Text>
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
