import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post } from "@/src/api";
import { Button } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

type ProgressData = {
  weights: Array<{ weight_kg: number; date: string }>;
  activities: Array<Record<string, unknown>>;
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

  const weights = (progress?.weights || []).map((item, index) => ({ ...item, date: `${item.date || "entry"}-${index}` }));

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="progress-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA</Text>
          <Text style={styles.headerTitle}>{t.progress}</Text>
        </View>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionSub}>{t.progressSub}</Text>
        <View style={styles.chartCard} testID="weight-chart">
          <Text style={styles.cardEyebrow}>WEIGHT TREND</Text>
          <View style={styles.chart}>
            {(weights.length ? weights.slice(-7) : [{ weight_kg: 0, date: "empty" }]).map((item, index) => (
              <View key={`${item.date || index}`} style={styles.chartCol}>
                <View style={[styles.chartBar, { height: Math.max(12, Math.min(120, item.weight_kg ? item.weight_kg * 1.2 : 18)) }]} />
                <Text style={styles.chartLabel}>{item.weight_kg ? `${item.weight_kg}` : "—"}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.mutedText}>Log a few days to see a personal trend emerge.</Text>
        </View>
        <View style={styles.inlineForm}>
          <TextInput testID="weight-input" value={weight} onChangeText={setWeight} placeholder="e.g. 68.5" placeholderTextColor={styles.placeholder.color as string} keyboardType="numeric" style={styles.inlineInput} />
          <Button testID="log-weight-button" label={busy ? "..." : t.log} onPress={save} disabled={busy || !weight} />
        </View>
        <View style={styles.reasonCard}>
          <Text style={styles.cardEyebrow}>{t.review.toUpperCase()}</Text>
          <Text style={styles.reasonText}>{progress?.review || "Your weekly review will appear after you log a few meals and movement sessions."}</Text>
        </View>
        <Text style={styles.disclaimer}>{t.disclaimer}</Text>
      </ScrollView>
    </View>
  );
}
