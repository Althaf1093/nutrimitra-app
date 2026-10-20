import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post, put } from "@/src/api";
import { COOKING_TIMES, KitchenEditor, type KitchenDraft } from "@/src/components/kitchen-editor";
import { ToastProvider, useToast } from "@/src/components/toast";
import { AppIcon, Button } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Kitchen, Plan } from "@/src/types";

export default function KitchenScreen() {
  // Its own toast host: on a phone a modal screen covers the app's main one.
  return (
    <ToastProvider bottom={24}>
      <MyKitchen />
    </ToastProvider>
  );
}

// Settings > My Kitchen: change what you have at home at any time; after saving, offer to update the plan.
function MyKitchen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const { profile, t, status } = useAuth();
  const [draft, setDraft] = useState<KitchenDraft | null>(null);
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [planUpdated, setPlanUpdated] = useState(false);
  const profileCookingTime = String(profile?.cooking_time || COOKING_TIMES[1]);

  useEffect(() => {
    if (status !== "ready") return;
    api<{ configured: boolean; kitchen: Kitchen | null }>("/kitchen")
      .then(({ kitchen }) => setDraft({ items: kitchen?.items ?? [], meals_per_day: kitchen?.meals_per_day ?? 3, household_size: kitchen?.household_size ?? 2, cooking_time: kitchen?.cooking_time ?? profileCookingTime }))
      .catch(() => setFailed(true));
  }, [status, profileCookingTime]);

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

  const change = (next: KitchenDraft) => {
    setDraft(next);
    setSaved(false);
    setPlanUpdated(false);
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      await put("/kitchen", draft);
      setSaved(true);
      toast.show(t.kitchenSaved);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : t.kitchenSaveFailed, { type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const updatePlan = async () => {
    setUpdating(true);
    try {
      await post<Plan>("/plan/regenerate", {});
      setPlanUpdated(true);
      toast.show(t.planRefreshed);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : t.couldNotRefresh, { type: "error" });
    } finally {
      setUpdating(false);
    }
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="kitchen-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>{t.kitchenEyebrow.toUpperCase()}</Text>
          <Text style={styles.headerTitle}>{t.settingsKitchen}</Text>
        </View>
        <Pressable testID="kitchen-close" accessibilityRole="button" accessibilityLabel={t.close} onPress={() => router.back()} style={styles.iconButton}>
          <AppIcon name="xmark" color={colors.onSurface} size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {!draft && !failed ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 24 }} /> : null}
        {failed ? (
          <View style={styles.reasonCard} testID="kitchen-failed">
            <Text style={styles.reasonText}>{t.couldNotLoad}</Text>
          </View>
        ) : null}
        {draft ? (
          <View>
            <KitchenEditor value={draft} onChange={change} />
            {saved ? (
              <View style={styles.reasonCard} testID="kitchen-saved-card">
                <Text style={styles.cardEyebrow}>{t.kitchenSaved.toUpperCase()}</Text>
                <Text style={styles.reasonText}>{planUpdated ? t.planRefreshed : t.kitchenUpdatePrompt}</Text>
                {!planUpdated ? (
                  <View style={{ marginTop: 12 }}>
                    <Button testID="kitchen-update-plan" label={updating ? "..." : t.updatePlan} onPress={updatePlan} disabled={updating} />
                    <Button testID="kitchen-not-now" label={t.kitchenNotNow} onPress={() => router.back()} secondary disabled={updating} />
                  </View>
                ) : (
                  <View style={{ marginTop: 12 }}>
                    <Button testID="kitchen-done" label={t.close} onPress={() => router.back()} secondary />
                  </View>
                )}
              </View>
            ) : null}
            <View style={{ marginTop: 18 }}>
              <Button testID="kitchen-save" label={saving ? "..." : t.kitchenSave} onPress={save} disabled={saving} />
            </View>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}
