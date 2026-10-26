import { Text, TextInput, View } from "react-native";

import { Button, Chip } from "@/src/components/ui";
import { confidenceLabel, mealTypeLabel, type Copy, type Lang } from "@/src/i18n";
import type { useStyles } from "@/src/styles";
import type { ThemeColors } from "@/src/theme";
import type { VisionResult } from "@/src/types";

export type VisionDraft = { name: string; calories: string; protein_g: string; carbs_g: string; fat_g: string; fibre_g: string; portion: string };

const mealTypes = ["breakfast", "lunch", "snack", "dinner"];

export function VisionConfirmForm({
  result,
  draft,
  setDraft,
  mealType,
  setMealType,
  error,
  busy,
  lang,
  t,
  styles,
  colors,
  onConfirm,
  onRetry,
}: {
  result: VisionResult;
  draft: VisionDraft;
  setDraft: (updater: (current: VisionDraft) => VisionDraft) => void;
  mealType: string;
  setMealType: (type: string) => void;
  error: string;
  busy: boolean;
  lang: Lang;
  t: Copy;
  styles: ReturnType<typeof useStyles>;
  colors: ThemeColors;
  onConfirm: () => void;
  onRetry: () => void;
}) {
  const numericField = (key: keyof VisionDraft, label: string) => (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput testID={`vision-field-${key}`} value={draft[key]} onChangeText={(v) => setDraft((current) => ({ ...current, [key]: v }))} keyboardType={key === "name" || key === "portion" ? "default" : "numeric"} placeholderTextColor={colors.muted} style={styles.input} />
    </View>
  );

  return (
    <View testID="vision-confirm">
      <Text style={styles.sectionTitleSmall}>{t.confirmMeal}</Text>
      <Text style={styles.modalSub}>
        {t.adjust} · {confidenceLabel(t, result.confidence)} {t.confidenceWord}
      </Text>
      {numericField("name", t.dishName)}
      <View style={styles.row}>
        <View style={styles.half}>{numericField("calories", "kcal")}</View>
        <View style={styles.half}>{numericField("protein_g", t.proteinLabel)}</View>
      </View>
      <View style={styles.row}>
        <View style={styles.half}>{numericField("carbs_g", t.carbsLabel)}</View>
        <View style={styles.half}>{numericField("fat_g", t.fatLabel)}</View>
      </View>
      {numericField("fibre_g", t.fibreLabel)}
      {numericField("portion", t.portionLabel)}
      <Text style={styles.fieldLabel}>{t.mealType}</Text>
      <View style={styles.chipWrap}>
        {mealTypes.map((item) => (
          <Chip key={item} label={item} text={mealTypeLabel(t, item)} selected={mealType === item} onPress={() => setMealType(item)} />
        ))}
      </View>
      {result.alternatives.length ? (
        <>
          <Text style={styles.fieldLabel}>{t.instead}</Text>
          <View style={styles.chipWrap}>
            {result.alternatives.map((item) => (
              <Chip key={item} label={item} selected={draft.name === item} onPress={() => setDraft((current) => ({ ...current, name: item }))} />
            ))}
          </View>
        </>
      ) : null}
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      <Button testID="vision-confirm-button" label={busy ? "..." : t.confirmLog} onPress={onConfirm} disabled={busy} />
      <Button testID="vision-retry-button" label={t.tryAgain} onPress={onRetry} secondary />
      <Text style={styles.disclaimer}>{t.photoDisclaimer}</Text>
    </View>
  );
}
