import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post } from "@/src/api";
import { Chip, MealCard } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import type { Meal, Plan } from "@/src/types";

export default function PlanScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { t } = useAuth();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [day, setDay] = useState(0);
  const [message, setMessage] = useState("");

  useFocusEffect(
    useCallback(() => {
      api<Plan>("/plan")
        .then(setPlan)
        .catch(() => undefined);
    }, []),
  );

  const logMeal = async (meal: Meal) => {
    try {
      await post("/meals", { meal_type: meal.type, name: meal.name, calories: meal.calories, protein_g: meal.protein_g, carbs_g: meal.carbs_g, fat_g: meal.fat_g, source: "plan" });
      setMessage(t.addMeal);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not log meal");
    }
  };

  const selected = plan?.days?.[day];

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="plan-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA · 7 DAYS</Text>
          <Text style={styles.headerTitle}>{t.plan}</Text>
        </View>
      </View>
      <View style={{ height: 56, flexGrow: 0 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dayRow}>
          {plan?.days?.map((item, index) => (
            <Chip key={item.day} label={`Day ${item.day}`} selected={day === index} onPress={() => setDay(index)} />
          ))}
        </ScrollView>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionSub}>{plan?.goal || "Your adaptable 7-day rhythm"}</Text>
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
              <Text style={styles.cardEyebrow}>NUTRITION NOTE</Text>
              <Text style={styles.reasonText}>{plan?.reasoning}</Text>
            </View>
          </>
        ) : (
          <View style={styles.center}>
            <Text style={styles.mutedText}>Complete onboarding to generate your plan.</Text>
          </View>
        )}
      </ScrollView>
      {message ? (
        <Chip label={message} selected onPress={() => setMessage("")} />
      ) : null}
    </View>
  );
}
