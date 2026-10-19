import { useEffect, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, useWindowDimensions, View } from "react-native";

import { api } from "@/src/api";
import { Button } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { mealTypeLabel } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Meal } from "@/src/types";

export type SwapTarget = { day: number; type: string };

// "Swap this meal": three other meals for the same slot, from the same kitchen. Errors stay inside the sheet because on a
// phone a modal covers the app's toast.
export function SwapSheet({ target, busy, onChoose, onClose }: { target: SwapTarget | null; busy: boolean; onChoose: (meal: Meal) => void; onClose: () => void }) {
  const styles = useStyles();
  const { t } = useAuth();
  return (
    <Modal visible={target !== null} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.sheetBackdrop} onPress={onClose} accessibilityLabel={t.close} testID="swap-sheet-backdrop">
        <Pressable style={{ width: "100%", alignItems: "center" }} onPress={() => undefined} accessible={false}>
          {target ? <SwapBody key={`${target.day}-${target.type}`} target={target} busy={busy} onChoose={onChoose} onClose={onClose} /> : null}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function SwapBody({ target, busy, onChoose, onClose }: { target: SwapTarget; busy: boolean; onChoose: (meal: Meal) => void; onClose: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { lang, t } = useAuth();
  const { height } = useWindowDimensions();
  const [options, setOptions] = useState<Meal[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api<{ alternatives: Meal[] }>(`/plan/swap?day=${target.day}&type=${encodeURIComponent(target.type)}`)
      .then((result) => {
        if (!cancelled) setOptions(result.alternatives);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [target.day, target.type]);

  const label = (item: { name: string; te?: string }) => (lang === "te" && item.te ? item.te : item.name);

  return (
    <View style={[styles.sheet, { maxHeight: Math.round(height * 0.92) }]} testID="swap-sheet">
      <View style={styles.sheetHandle} />
      <ScrollView style={{ flexGrow: 0 }} showsVerticalScrollIndicator={false}>
        <Text style={styles.sheetTitle}>{t.swapTitle}</Text>
        <Text style={styles.mutedText}>
          {mealTypeLabel(t, target.type)} · {t.swapSub}
        </Text>
        {!options && !failed ? <ActivityIndicator color={colors.brandPrimary} style={{ marginVertical: 24 }} /> : null}
        {failed ? (
          <Text style={[styles.errorText, { marginTop: 14 }]} testID="swap-failed">
            {t.couldNotSwap}
          </Text>
        ) : null}
        {options && options.length === 0 ? (
          <Text style={[styles.reasonText, { marginTop: 14 }]} testID="swap-none">
            {t.swapNone}
          </Text>
        ) : null}
        {options?.map((meal, index) => (
          <View key={meal.name} style={styles.foodRow} testID={`swap-option-${index}`}>
            <View style={styles.flex}>
              <Text style={styles.foodName}>{label(meal)}</Text>
              <Text style={styles.foodMeta}>
                {meal.calories} kcal · {meal.protein_g}g {t.proteinWord}
                {meal.minutes ? ` · ${meal.minutes} ${t.minutes}` : ""}
              </Text>
              {meal.uses?.length ? (
                <Text style={styles.foodMeta}>
                  {t.usesWord}: {meal.uses.map((item) => `${lang === "te" && item.te ? item.te : item.name.split("(")[0].trim()}${item.have ? "" : ` (${t.buyWord})`}`).join(", ")}
                </Text>
              ) : null}
            </View>
            <Pressable testID={`swap-use-${index}`} accessibilityRole="button" accessibilityLabel={`${t.swapUse}: ${label(meal)}`} disabled={busy} onPress={() => onChoose(meal)} style={[styles.chip, busy && styles.disabled]}>
              <Text style={styles.chipText}>{t.swapUse}</Text>
            </Pressable>
          </View>
        ))}
        <Button testID="swap-cancel" label={t.cancel} secondary onPress={onClose} />
      </ScrollView>
    </View>
  );
}
