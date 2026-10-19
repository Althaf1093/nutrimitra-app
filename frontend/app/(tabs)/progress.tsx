import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, post } from "@/src/api";
import { Button } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

type ProgressData = {
  weights: { id: string; weight_kg: number; date: string }[];
  activities: Record<string, unknown>[];
  review: string;
};

export default function ProgressScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { t } = useAuth();
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [weight, setWeight] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<ProgressData>("/progress")
      .then(setProgress)
      .catch(() => undefined);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const save = async () => {
    if (!weight) return;
    setBusy(true);
    try {
      await post("/weight", { weight_kg: Number(weight) });
      setWeight("");
      load();
    } finally {
      setBusy(false);
    }
  };

  const removeWeight = async (id: string) => {
    setBusy(true);
    try {
      await del(`/weight/${id}`);
      load();
    } finally {
      setBusy(false);
    }
  };

  const entries = [...(progress?.weights || [])].reverse().slice(0, 10);
  const weights = (progress?.weights || []).map((item, index) => ({ ...item, date: `${item.date || "entry"}-${index}` }));

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="progress-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>WELLSTRIDE</Text>
          <Text style={styles.headerTitle}>{t.progress}</Text>
        </View>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionSub}>{t.progressSub}</Text>
        <View style={styles.chartCard} testID="weight-chart">
          <Text style={styles.cardEyebrow}>{t.weightTrend.toUpperCase()}</Text>
          <View style={styles.chart}>
            {(weights.length ? weights.slice(-7) : [{ weight_kg: 0, date: "empty" }]).map((item, index) => (
              <View key={`${item.date || index}`} style={styles.chartCol}>
                <View style={[styles.chartBar, { height: Math.max(12, Math.min(120, item.weight_kg ? item.weight_kg * 1.2 : 18)) }]} />
                <Text style={styles.chartLabel}>{item.weight_kg ? `${item.weight_kg}` : "—"}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.mutedText}>{t.trendHint}</Text>
        </View>
        <View style={styles.inlineForm}>
          <TextInput testID="weight-input" value={weight} onChangeText={setWeight} placeholder={t.weightPlaceholder} placeholderTextColor={styles.placeholder.color as string} keyboardType="numeric" style={styles.inlineInput} />
          <Button testID="log-weight-button" label={busy ? "..." : t.log} onPress={save} disabled={busy || !weight} />
        </View>
        {entries.length ? (
          <View style={styles.reasonCard} testID="weight-entries">
            <Text style={styles.cardEyebrow}>{t.weightEntries.toUpperCase()}</Text>
            {entries.map((item) => (
              <View key={item.id} style={styles.logRow} testID={`weight-entry-${item.id}`}>
                <View style={styles.flex}>
                  <Text style={styles.mealName}>{item.weight_kg} kg</Text>
                  <Text style={styles.mealMeta}>{item.date}</Text>
                </View>
                <Pressable testID={`remove-weight-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.remove} ${item.weight_kg} kg`} disabled={busy} onPress={() => removeWeight(item.id)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                  <Text style={styles.linkText}>{t.remove}</Text>
                </Pressable>
              </View>
            ))}
          </View>
        ) : null}
        <View style={styles.reasonCard}>
          <Text style={styles.cardEyebrow}>{t.review.toUpperCase()}</Text>
          <Text style={styles.reasonText}>{progress?.review || t.reviewEmpty}</Text>
        </View>
        <Text style={styles.disclaimer}>{t.disclaimer}</Text>
      </ScrollView>
    </View>
  );
}
