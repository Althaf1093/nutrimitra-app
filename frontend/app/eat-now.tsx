import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post } from "@/src/api";
import { AppIcon, Button } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { EatNow } from "@/src/types";

export default function EatNowScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { t, status } = useAuth();
  const [data, setData] = useState<EatNow | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status !== "ready") return;
    api<EatNow>("/eat-now")
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not fetch recommendation"));
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

  const log = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const meal = data.suggestion;
      await post("/meals", { meal_type: meal.type, name: meal.name, calories: meal.calories, protein_g: meal.protein_g, carbs_g: meal.carbs_g, fat_g: meal.fat_g, source: "eat-now" });
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log meal");
      setBusy(false);
    }
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="eat-now-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA PICK</Text>
          <Text style={styles.headerTitle}>{t.eatNow}</Text>
        </View>
        <Pressable testID="eat-now-close" accessibilityRole="button" accessibilityLabel={t.close} onPress={() => router.back()} style={styles.iconButton}>
          <AppIcon name="xmark" color={colors.onSurface} size={20} />
        </Pressable>
      </View>
      {!data && !error ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brandPrimary} />
          <Text style={styles.mutedText}>Analyzing your day so far…</Text>
        </View>
      ) : error ? (
        <View style={[styles.center, { padding: 24 }]}>
          <Text style={styles.errorText} testID="eat-now-error">
            {error}
          </Text>
          <Button label={t.notNow} onPress={() => router.back()} secondary />
        </View>
      ) : data ? (
        <>
          <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
            <View style={styles.readinessCard} testID="eat-now-remaining">
              <View style={styles.flex}>
                <Text style={styles.cardEyebrowOnDark}>ENERGY BALANCE</Text>
                <Text style={styles.readinessValue}>{data.remaining_calories}</Text>
                <Text style={styles.cardCaption}>{t.remaining}</Text>
              </View>
              <View style={styles.readinessRing}>
                <Text style={styles.ringText}>{data.consumed_calories}</Text>
                <Text style={styles.ringCaption}>of {data.target_calories} kcal</Text>
              </View>
            </View>
            <Text style={styles.modalMeal} testID="eat-now-meal-name">
              {data.suggestion.name}
            </Text>
            <Text style={styles.reasonText}>{data.reasoning}</Text>
            <View style={styles.macroRow}>
              <Text style={styles.macro}>{data.suggestion.calories} kcal</Text>
              <Text style={styles.macro}>{data.suggestion.protein_g}g protein</Text>
              <Text style={styles.macro}>{data.suggestion.carbs_g}g carbs</Text>
              <Text style={styles.macro}>{data.suggestion.fat_g}g fat</Text>
              <Text style={styles.macro}>{data.suggestion.portion}</Text>
            </View>
            <View style={styles.reasonCard}>
              <Text style={styles.cardEyebrow}>SAFETY</Text>
              <Text style={styles.reasonText}>{data.disclaimer}</Text>
            </View>
          </ScrollView>
          <View style={[styles.stickyCta, { paddingBottom: Math.max(insets.bottom, 16) }]}>
            <Button testID="eat-now-log-button" label={busy ? "..." : t.logThis} onPress={log} disabled={busy} />
            <Button testID="eat-now-dismiss-button" label={t.notNow} onPress={() => router.back()} secondary />
          </View>
        </>
      ) : null}
    </View>
  );
}
