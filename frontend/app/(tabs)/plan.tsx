import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, isAiBusy, post } from "@/src/api";
import { useToast } from "@/src/components/toast";
import { AppIcon, Chip, MealCard } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { optionLabel } from "@/src/i18n";
import { markPlanMeal, planMealBody } from "@/src/lib/plan";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { LoggedMeal, Meal, Plan } from "@/src/types";

export default function PlanScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { t } = useAuth();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [day, setDay] = useState(0);
  const toast = useToast();
  const [refreshing, setRefreshing] = useState(false);

  const refreshPlan = async () => {
    setRefreshing(true);
    try {
      const next = await post<Plan>("/plan/regenerate", {});
      setPlan(next);
      setDay(next.today_index ?? 0);
      toast.show(t.planRefreshed);
    } catch (err) {
      toast.show(isAiBusy(err) ? t.aiBusy : err instanceof Error ? err.message : t.couldNotRefresh, { type: "error" });
    } finally {
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      api<Plan>("/plan")
        .then((next) => {
          setPlan(next);
          setDay(next.today_index ?? 0);
        })
        .catch(() => undefined);
    }, []),
  );

  const undoLog = async (id: string) => {
    try {
      await del(`/meals/${id}`);
      toast.show(t.undone, { type: "info" });
    } catch (err) {
      toast.show(err instanceof Error ? err.message : t.couldNotUndo, { type: "error" });
    }
    const fresh = await api<Plan>("/plan").catch(() => null);
    if (fresh) setPlan(fresh);
  };

  const logMeal = async (meal: Meal) => {
    // Optimistic: the "+" becomes the check at once; the server's answer confirms it or rolls it back.
    const dayIndex = day;
    setPlan((current) => (current ? markPlanMeal(current, dayIndex, meal, true) : current));
    try {
      const saved = await post<LoggedMeal>("/meals", planMealBody(meal));
      toast.show(t.addMeal, { actionLabel: t.undo, onAction: () => undoLog(saved.id) });
      // Re-fetch so today's logged meals show as done instead of "+".
      setPlan(await api<Plan>("/plan"));
    } catch (err) {
      setPlan((current) => (current ? markPlanMeal(current, dayIndex, meal, false) : current));
      toast.show(err instanceof Error ? err.message : t.couldNotLogMeal, { type: "error" });
    }
  };

  const selected = plan?.days?.[day];

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="plan-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>WELLSTRIDE · {t.sevenDays.toUpperCase()}</Text>
          <Text style={styles.headerTitle}>{t.plan}</Text>
        </View>
        <Pressable testID="refresh-plan-button" accessibilityRole="button" accessibilityLabel={t.refreshPlan} disabled={refreshing} onPress={refreshPlan} style={[styles.iconButton, refreshing && styles.disabled]}>
          <AppIcon name="arrow.clockwise" color={colors.brandPrimary} size={20} />
        </Pressable>
      </View>
      <View style={{ height: 56, flexGrow: 0 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dayRow}>
          {plan?.days?.map((item, index) => (
            <Chip key={item.day} label={index === plan.today_index ? `${t.dayWord} ${item.day} · ${t.today}` : `${t.dayWord} ${item.day}`} selected={day === index} onPress={() => setDay(index)} />
          ))}
        </ScrollView>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionSub}>{plan?.goal ? optionLabel(t, plan.goal) : t.planRhythm}</Text>
        <Text style={[styles.disclaimer, { marginTop: 4, marginBottom: 8 }]} testID="plan-wellness-notice">
          {t.wellnessNotice}
        </Text>
        {plan?.ai_status ? (
          <View style={styles.reasonCard} testID="plan-ai-busy">
            <Text style={styles.reasonText}>{plan.ai_status === "ai_busy" ? t.aiBusyPlan : t.aiUnavailable}</Text>
          </View>
        ) : null}
        {selected ? (
          <>
            <View style={styles.planIntro}>
              <Text style={styles.planDay}>{selected.title}</Text>
              <Text style={styles.mutedText}>{selected.focus}</Text>
            </View>
            {selected.meals.map((meal) => (
              <MealCard key={`${meal.type}-${meal.name}`} meal={meal} onLog={() => logMeal(meal)} />
            ))}
            <View style={styles.reasonCard}>
              <Text style={styles.cardEyebrow}>{t.nutritionNote.toUpperCase()}</Text>
              <Text style={styles.reasonText}>{plan?.reasoning}</Text>
            </View>
          </>
        ) : (
          <View style={styles.center}>
            <Text style={styles.mutedText}>{t.planEmpty}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}
