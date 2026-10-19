import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Text, View } from "react-native";

import { post } from "@/src/api";
import { Button } from "@/src/components/ui";
import { VisionConfirmForm, type VisionDraft } from "@/src/components/vision-confirm-form";
import { useAuth } from "@/src/context/auth";
import { defaultSlot } from "@/src/lib/food";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { VisionResult } from "@/src/types";

type Phase = "pick" | "analyzing" | "confirm" | "error";

// The photo path of Log food: take or choose a picture, check the estimate, save it as a meal.
export function PhotoLogger({ onLogged, onBack }: { onLogged: () => void; onBack: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { lang, t } = useAuth();
  const [phase, setPhase] = useState<Phase>("pick");
  const [imageUri, setImageUri] = useState("");
  const [result, setResult] = useState<VisionResult | null>(null);
  const [draft, setDraft] = useState<VisionDraft>({ name: "", calories: "", protein_g: "", carbs_g: "", fat_g: "", portion: "" });
  const [mealType, setMealType] = useState(defaultSlot());
  const [error, setError] = useState("");
  const [blocked, setBlocked] = useState(false);
  const [busy, setBusy] = useState(false);

  const analyze = async (base64: string) => {
    setPhase("analyzing");
    setError("");
    try {
      const vision = await post<VisionResult>("/coach/vision", { image_base64: base64, language: lang, meal_type: mealType });
      setResult(vision);
      setDraft({
        name: vision.name,
        calories: String(vision.calories),
        protein_g: String(vision.protein_g),
        carbs_g: String(vision.carbs_g),
        fat_g: String(vision.fat_g),
        portion: vision.portion,
      });
      setPhase("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.photoFailed);
      setPhase("error");
    }
  };

  const pick = async (kind: "camera" | "library") => {
    setError("");
    setBlocked(false);
    if (Platform.OS !== "web") {
      const current = kind === "camera" ? await ImagePicker.getCameraPermissionsAsync() : await ImagePicker.getMediaLibraryPermissionsAsync();
      let granted = current.status === "granted";
      let canAsk = current.canAskAgain;
      if (!granted && canAsk) {
        const requested = kind === "camera" ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
        granted = requested.status === "granted";
        canAsk = requested.canAskAgain;
      }
      if (!granted) {
        setBlocked(!canAsk);
        setError(t.cameraBlocked);
        return;
      }
    }
    try {
      const options: ImagePicker.ImagePickerOptions = { base64: true, quality: 0.4, mediaTypes: ["images"] };
      const picked = kind === "camera" ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
      const asset = picked.assets?.[0];
      if (picked.canceled || !asset?.base64) return;
      setImageUri(asset.uri);
      await analyze(asset.base64);
    } catch {
      setError(t.photoFailed);
      setPhase("error");
    }
  };

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      await post("/meals", {
        meal_type: mealType,
        name: draft.name.trim() || t.photoMealName,
        calories: Math.max(0, Math.round(Number(draft.calories) || 0)),
        protein_g: Math.max(0, Number(draft.protein_g) || 0),
        carbs_g: Math.max(0, Number(draft.carbs_g) || 0),
        fat_g: Math.max(0, Number(draft.fat_g) || 0),
        source: "photo estimate",
      });
      onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.couldNotLogMeal);
      setBusy(false);
    }
  };

  return (
    <View testID="photo-logger">
      <Text style={styles.modalSub}>{t.photoSub}</Text>
      {imageUri ? <Image source={{ uri: imageUri }} style={styles.photoPreview} contentFit="cover" testID="food-photo-preview" /> : null}
      {phase === "analyzing" ? (
        <View style={[styles.center, { minHeight: 160 }]} testID="vision-analyzing">
          <ActivityIndicator color={colors.brandPrimary} />
          <Text style={styles.mutedText}>{t.identifying}</Text>
        </View>
      ) : null}
      {phase === "pick" || phase === "error" ? (
        <View>
          {error ? (
            <View style={styles.reasonCard} testID="vision-error">
              <Text style={styles.cardEyebrow}>{t.photoCard.toUpperCase()}</Text>
              <Text style={styles.reasonText}>{error}</Text>
              {blocked ? (
                <View style={{ marginTop: 12 }}>
                  <Button testID="open-system-settings-button" label={t.openSettings} onPress={() => Linking.openSettings()} secondary />
                </View>
              ) : null}
            </View>
          ) : null}
          <View style={{ marginTop: 16, gap: 4 }}>
            <Button testID="take-photo-button" label={t.takePhoto} onPress={() => pick("camera")} />
            <Button testID="choose-photo-button" label={t.choosePhoto} onPress={() => pick("library")} secondary />
            <Button testID="photo-back-button" label={t.backToSearch} onPress={onBack} secondary />
          </View>
          <Text style={styles.disclaimer}>{t.cameraWhy}</Text>
        </View>
      ) : null}
      {phase === "confirm" && result ? (
        <VisionConfirmForm
          result={result}
          draft={draft}
          setDraft={setDraft}
          mealType={mealType}
          setMealType={setMealType}
          error={error}
          busy={busy}
          lang={lang}
          t={t}
          styles={styles}
          colors={colors}
          onConfirm={confirm}
          onRetry={() => {
            setPhase("pick");
            setImageUri("");
            setResult(null);
          }}
        />
      ) : null}
    </View>
  );
}
