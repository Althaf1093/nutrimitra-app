import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { put } from "@/src/api";
import { Button, Chip, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import type { Profile } from "@/src/types";

const goals = ["Weight loss", "Weight gain", "Maintenance", "Muscle building", "Fitness", "Healthier living"];
const diets = ["Vegetarian", "Eggetarian", "Non-vegetarian", "Vegan"];
const activityLevels = ["Lightly active", "Moderately active", "Very active"];

export default function OnboardingScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { lang, t, completeOnboarding } = useAuth();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Record<string, unknown>>({
    age: "30",
    sex: "Prefer not to say",
    height_cm: "165",
    weight_kg: "70",
    target_weight_kg: "65",
    conditions: [],
    dietary_preferences: ["Vegetarian"],
    allergies: [],
    disliked_foods: [],
    activity_level: "Moderately active",
    cooking_time: "20–30 min",
    food_budget: "Balanced",
    wellness_goal: "Healthier living",
    language: lang,
  });
  const set = (key: string, value: unknown) => setDraft((current) => ({ ...current, [key]: value }));
  const toggle = (key: string, value: string) => {
    const current = (draft[key] as string[]) || [];
    set(key, current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  };
  const finish = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...draft,
        age: Number(draft.age),
        height_cm: Number(draft.height_cm),
        weight_kg: Number(draft.weight_kg),
        target_weight_kg: Number(draft.target_weight_kg),
      };
      const result = await put<{ profile: Profile }>("/profile", payload);
      completeOnboarding(result.profile);
      router.replace("/(tabs)");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="onboarding-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.onboardingContent} keyboardShouldPersistTaps="handled">
        <View style={styles.stepTop}>
          <Text style={styles.eyebrow}>NUTRIMITRA · {step + 1} / 3</Text>
          <Text style={styles.stepCounter}>{step === 0 ? t.body : step === 1 ? t.preferences : t.rhythm}</Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${((step + 1) / 3) * 100}%` }]} />
        </View>
        <Text style={styles.sectionTitle}>{t.profileTitle}</Text>
        <Text style={styles.sectionSub}>{t.profileSub}</Text>
        {step === 0 ? (
          <View style={styles.formStack}>
            <Field label={t.age} value={String(draft.age)} onChangeText={(v) => set("age", v)} keyboardType="numeric" />
            <View style={styles.field}>
              <Text style={styles.fieldLabel}>{t.sex}</Text>
              <View style={styles.chipWrap}>
                {["Female", "Male", "Prefer not to say"].map((item) => (
                  <Chip key={item} label={item} selected={draft.sex === item} onPress={() => set("sex", item)} />
                ))}
              </View>
            </View>
            <Field label={t.height} value={String(draft.height_cm)} onChangeText={(v) => set("height_cm", v)} keyboardType="numeric" />
            <View style={styles.row}>
              <View style={styles.half}>
                <Field label={t.weight} value={String(draft.weight_kg)} onChangeText={(v) => set("weight_kg", v)} keyboardType="numeric" />
              </View>
              <View style={styles.half}>
                <Field label={t.target} value={String(draft.target_weight_kg)} onChangeText={(v) => set("target_weight_kg", v)} keyboardType="numeric" />
              </View>
            </View>
          </View>
        ) : step === 1 ? (
          <View style={styles.formStack}>
            <Text style={styles.fieldLabel}>{t.goal}</Text>
            <View style={styles.chipWrap}>
              {goals.map((item) => (
                <Chip key={item} label={item} selected={draft.wellness_goal === item} onPress={() => set("wellness_goal", item)} />
              ))}
            </View>
            <Text style={styles.fieldLabel}>{t.diet}</Text>
            <View style={styles.chipWrap}>
              {diets.map((item) => (
                <Chip key={item} label={item} selected={(draft.dietary_preferences as string[]).includes(item)} onPress={() => toggle("dietary_preferences", item)} />
              ))}
            </View>
            <Field label={t.conditions} value={(draft.conditions as string[]).join(", ")} onChangeText={(v) => set("conditions", v.split(",").map((x) => x.trim()).filter(Boolean))} placeholder="e.g. PCOS, diabetes" />
            <Field label={t.allergies} value={(draft.allergies as string[]).join(", ")} onChangeText={(v) => set("allergies", v.split(",").map((x) => x.trim()).filter(Boolean))} placeholder="e.g. peanuts" />
            <Field label={t.dislikes} value={(draft.disliked_foods as string[]).join(", ")} onChangeText={(v) => set("disliked_foods", v.split(",").map((x) => x.trim()).filter(Boolean))} placeholder="e.g. bitter gourd" />
          </View>
        ) : (
          <View style={styles.formStack}>
            <Text style={styles.fieldLabel}>{t.activity}</Text>
            <View style={styles.chipWrap}>
              {activityLevels.map((item) => (
                <Chip key={item} label={item} selected={draft.activity_level === item} onPress={() => set("activity_level", item)} />
              ))}
            </View>
            <Text style={styles.fieldLabel}>{t.cooking}</Text>
            <View style={styles.chipWrap}>
              {["Under 15 min", "20–30 min", "I enjoy cooking"].map((item) => (
                <Chip key={item} label={item} selected={draft.cooking_time === item} onPress={() => set("cooking_time", item)} />
              ))}
            </View>
            <Text style={styles.fieldLabel}>{t.budget}</Text>
            <View style={styles.chipWrap}>
              {["Budget-friendly", "Balanced", "Flexible"].map((item) => (
                <Chip key={item} label={item} selected={draft.food_budget === item} onPress={() => set("food_budget", item)} />
              ))}
            </View>
            <Text style={styles.fieldLabel}>{t.language}</Text>
            <View style={styles.chipWrap}>
              <Chip label="English" selected={draft.language === "en"} onPress={() => set("language", "en")} />
              <Chip label="తెలుగు" selected={draft.language === "te"} onPress={() => set("language", "te")} />
            </View>
          </View>
        )}
        {error ? <Text style={styles.errorText} testID="onboarding-error">{error}</Text> : null}
        <View style={styles.stickyActions}>
          {step > 0 ? <Button label="Back" onPress={() => setStep(step - 1)} secondary /> : null}
          <Button testID="onboarding-next-button" label={busy ? "Saving..." : step === 2 ? t.finish : t.continueNext} onPress={step === 2 ? finish : () => setStep(step + 1)} disabled={busy} />
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
