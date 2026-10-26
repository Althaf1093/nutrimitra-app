import { Pressable, Text, View } from "react-native";

import { AppIcon } from "@/src/components/icon";
import type { Copy } from "@/src/i18n";
import { makeStyles, radius, useTheme } from "@/src/theme";
import type { Dashboard, IngredientRef } from "@/src/types";

const useCards = makeStyles((colors) => ({
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: 16,
    boxShadow: colors.shadowCard,
  },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardLabel: { color: colors.muted, fontSize: 13, fontWeight: "700" },
  big: {
    color: colors.onCard,
    fontSize: 26,
    fontWeight: "800",
    marginTop: 8,
    fontVariant: ["tabular-nums"],
  },
  bigUnit: { color: colors.muted, fontSize: 13, fontWeight: "600" },
  track: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.waterSoft,
    marginTop: 10,
    overflow: "hidden",
  },
  fill: { height: 8, borderRadius: 4, backgroundColor: colors.water },
  waterRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  roundButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.waterSoft,
  },
  coachHead: { flexDirection: "row", alignItems: "center", gap: 10 },
  coachBadge: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  coachTitle: { color: colors.onCard, fontSize: 16, fontWeight: "800" },
  coachText: {
    color: colors.onCard,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 12,
  },
  eatNow: {
    minHeight: 48,
    marginTop: 14,
    paddingHorizontal: 16,
    borderRadius: 24,
    backgroundColor: colors.brandPrimary,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  eatNowText: {
    flex: 1,
    color: colors.onBrandPrimary,
    fontSize: 15,
    fontWeight: "700",
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  chip: {
    minHeight: 36,
    paddingHorizontal: 14,
    borderRadius: 18,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  chipText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  shop: {
    backgroundColor: colors.accentSoft,
    borderRadius: 24,
    padding: 20,
    gap: 10,
  },
  shopTitle: {
    color: colors.onAccentSoft,
    fontSize: 14,
    fontWeight: "800",
    flex: 1,
  },
  shopText: { color: colors.onAccentSoft, fontSize: 14, lineHeight: 21 },
}));

/** Water so far against a general daily guide, with a button to add a glass (250 ml) and one to take it back. */
export function WaterCard({
  dashboard,
  t,
  onAdd,
}: {
  dashboard: Dashboard | null;
  t: Copy;
  onAdd: (delta: number) => void;
}) {
  const styles = useCards();
  const { colors } = useTheme();
  const ml = dashboard?.water_ml || 0;
  const target = dashboard?.target_water_ml || 3000;
  const litres = (value: number) => String(Math.round(value / 100) / 10);
  return (
    <View style={styles.card} testID="water-card">
      <View style={styles.cardHead}>
        <AppIcon name="water" color={colors.water} size={18} />
        <Text style={styles.cardLabel}>{t.waterTitle}</Text>
      </View>
      <View style={styles.waterRow}>
        <Text style={styles.big} testID="water-value">
          {litres(ml)} <Text style={styles.bigUnit}>/ {litres(target)} L</Text>
        </Text>
        <View style={{ flexDirection: "row", gap: 8, marginTop: 8 }}>
          {ml > 0 ? (
            <Pressable
              testID="water-minus"
              accessibilityRole="button"
              accessibilityLabel={t.waterUndo}
              onPress={() => onAdd(-250)}
              style={({ pressed }) => [
                styles.roundButton,
                pressed && { opacity: 0.7 },
              ]}
            >
              <AppIcon name="remove" color={colors.water} size={18} />
            </Pressable>
          ) : null}
          <Pressable
            testID="water-plus"
            accessibilityRole="button"
            accessibilityLabel={t.waterAdd}
            onPress={() => onAdd(250)}
            style={({ pressed }) => [
              styles.roundButton,
              pressed && { opacity: 0.7 },
            ]}
          >
            <AppIcon name="add" color={colors.water} size={18} />
          </Pressable>
        </View>
      </View>
      <View
        style={styles.track}
        accessibilityRole="progressbar"
        accessibilityValue={{ min: 0, max: target, now: Math.min(ml, target) }}
      >
        <View
          style={[
            styles.fill,
            {
              width: `${Math.round(Math.max(0, Math.min(1, ml / target)) * 100)}%`,
            },
          ]}
        />
      </View>
    </View>
  );
}

// A short note from the plain numbers logged today. It reads the dashboard; it is not a model answer and not medical advice.
export function coachNote(dashboard: Dashboard | null, t: Copy): string {
  const eaten = dashboard?.calories || 0;
  const target = dashboard?.target_calories || 0;
  if (!eaten) return t.coachNothing;
  if (target && eaten >= target * 1.05) return t.coachAbove;
  const proteinTarget = dashboard?.target_protein_g || 0;
  if (
    proteinTarget &&
    (dashboard?.protein_g || 0) < proteinTarget * (eaten / target) * 0.75
  )
    return t.coachLowProtein;
  return t.coachOnTrack;
}

export function CoachCard({
  dashboard,
  t,
  onOpen,
  onEatNow,
}: {
  dashboard: Dashboard | null;
  t: Copy;
  onOpen: (prompt?: string) => void;
  onEatNow: () => void;
}) {
  const styles = useCards();
  const { colors } = useTheme();
  const chips = [t.coachChipProtein, t.coachChipCook, t.coachChipWalk];
  return (
    <View
      style={[styles.card, { padding: 20, borderRadius: 24 }]}
      testID="coach-card"
    >
      <View style={styles.coachHead}>
        <View style={styles.coachBadge}>
          <AppIcon name="coach" color={colors.onBrandPrimary} size={20} />
        </View>
        <Text style={styles.coachTitle}>{t.coachCardTitle}</Text>
      </View>
      <Text style={styles.coachText} testID="coach-card-text">
        {coachNote(dashboard, t)}
      </Text>
      <Pressable
        testID="eat-now-button"
        accessibilityRole="button"
        onPress={onEatNow}
        style={({ pressed }) => [styles.eatNow, pressed && { opacity: 0.85 }]}
      >
        <AppIcon name="sparkles" color={colors.onBrandPrimary} size={18} />
        <Text style={styles.eatNowText}>{t.eatNow}</Text>
        <AppIcon name="chevron.right" color={colors.onBrandPrimary} size={16} />
      </Pressable>
      <View style={styles.chips}>
        {chips.map((chip) => (
          <Pressable
            key={chip}
            accessibilityRole="button"
            accessibilityLabel={chip}
            onPress={() => onOpen(chip)}
            style={({ pressed }) => [styles.chip, pressed && { opacity: 0.7 }]}
          >
            <Text style={styles.chipText}>{chip}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

/** The week's missing ingredients, from the plan. Only shown when there is something to buy. */
export function ShoppingCard({
  toBuy,
  lang,
  t,
  onOpen,
}: {
  toBuy: IngredientRef[];
  lang: string;
  t: Copy;
  onOpen: () => void;
}) {
  const styles = useCards();
  const { colors } = useTheme();
  if (!toBuy.length) return null;
  const names = toBuy
    .slice(0, 4)
    .map((item) => (lang === "te" && item.te ? item.te : item.name));
  return (
    <Pressable
      testID="shopping-card"
      accessibilityRole="button"
      accessibilityLabel={t.shoppingList}
      onPress={onOpen}
      style={({ pressed }) => [styles.shop, pressed && { opacity: 0.85 }]}
    >
      <View style={styles.cardHead}>
        <AppIcon name="kitchen" color={colors.accent} size={18} />
        <Text style={styles.shopTitle}>
          {t.shoppingCardTitle.replace("{n}", String(toBuy.length))}
        </Text>
      </View>
      <Text style={styles.shopText}>
        {t.shoppingMissing.replace("{items}", names.join(", "))}
      </Text>
    </Pressable>
  );
}
