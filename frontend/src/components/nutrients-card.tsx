import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { AppIcon } from "@/src/components/icon";
import { useAuth } from "@/src/context/auth";
import { makeStyles, radius, useTheme } from "@/src/theme";
import type { NutrientDay, NutrientWeek } from "@/src/types";

const useCard = makeStyles((colors) => ({
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: 16,
    gap: 12,
    boxShadow: colors.shadowCard,
  },
  head: { flexDirection: "row", alignItems: "center", gap: 8 },
  title: { flex: 1, color: colors.onCard, fontSize: 16, fontWeight: "800" },
  sub: { color: colors.muted, fontSize: 12, lineHeight: 17 },
  list: { gap: 10 },
  row: { gap: 4 },
  rowHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    gap: 8,
  },
  name: { flex: 1, color: colors.onCard, fontSize: 13, fontWeight: "700" },
  value: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "600",
    fontVariant: ["tabular-nums"],
  },
  track: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.surfaceTertiary,
    overflow: "hidden",
  },
  fill: { height: 6, borderRadius: 3 },
  toggle: {
    alignSelf: "flex-start",
    minHeight: 36,
    justifyContent: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  toggleText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700" },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 12,
    minHeight: 32,
    borderRadius: 16,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  chipText: { color: colors.onAccentSoft, fontSize: 13, fontWeight: "700" },
  label: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  text: { color: colors.onCard, fontSize: 14, lineHeight: 21 },
}));

type Row = {
  key: string;
  en: string;
  te: string;
  unit: string;
  value: number | null;
  reference: number | null;
  percent: number | null;
  limit: boolean;
};

const number = (value: number | null) =>
  value === null ? "—" : String(Math.round(value * 10) / 10);

/** Today: small bars as a share of the daily reference, the three lowest highlighted, tap to see all. */
export function TodayNutrientsCard({
  nutrients,
}: {
  nutrients: NutrientDay[] | undefined;
}) {
  const styles = useCard();
  const { colors } = useTheme();
  const { t, lang } = useAuth();
  const [open, setOpen] = useState(false);
  const rows: Row[] = (nutrients || []).map((item) => ({
    key: item.key,
    en: item.en,
    te: item.te,
    unit: item.unit,
    value: item.total,
    reference: item.reference,
    percent: item.percent,
    limit: item.limit,
  }));
  const tracked = !!nutrients?.some((item) => item.tracked);
  const lowest = rows
    .filter((row) => !row.limit && row.percent !== null)
    .sort((a, b) => (a.percent as number) - (b.percent as number))
    .slice(0, 3)
    .map((row) => row.key);
  const shown = open ? rows : rows.filter((row) => lowest.includes(row.key));
  return (
    <View style={styles.card} testID="nutrients-card">
      <View style={styles.head}>
        <AppIcon name="sparkles" color={colors.accent} size={18} />
        <Text style={styles.title}>{t.nutrientsTitle}</Text>
      </View>
      {!tracked ? (
        <Text style={styles.sub} testID="nutrients-none">
          {t.nutrientsNone}
        </Text>
      ) : (
        <>
          <Text style={styles.label}>
            {open ? t.nutrientsAll : t.nutrientsLowest}
          </Text>
          <View style={styles.list} testID="nutrients-list">
            {shown.map((row) => (
              <NutrientRow
                key={row.key}
                row={row}
                lang={lang}
                lowest={lowest.includes(row.key)}
              />
            ))}
          </View>
          <Pressable
            testID="nutrients-toggle"
            accessibilityRole="button"
            accessibilityState={{ expanded: open }}
            onPress={() => setOpen(!open)}
            style={styles.toggle}
          >
            <Text style={styles.toggleText}>
              {open ? t.nutrientsHide : t.nutrientsShowAll}
            </Text>
            <AppIcon
              name={open ? "up" : "down"}
              color={colors.brandPrimary}
              size={16}
            />
          </Pressable>
          <Text style={styles.sub}>{t.nutrientsNote}</Text>
        </>
      )}
    </View>
  );
}

function NutrientRow({
  row,
  lang,
  lowest,
}: {
  row: Row;
  lang: string;
  lowest: boolean;
}) {
  const styles = useCard();
  const { colors } = useTheme();
  const { t } = useAuth();
  const fraction =
    row.percent === null ? 0 : Math.max(0, Math.min(1, row.percent / 100));
  const name = lang === "te" ? row.te : row.en;
  const reference = row.reference === null ? "" : ` / ${number(row.reference)}`;
  return (
    <View style={styles.row} testID={`nutrient-${row.key}`}>
      <View style={styles.rowHead}>
        <Text style={styles.name}>{name}</Text>
        <Text style={styles.value}>
          {number(row.value)}
          {reference} {row.unit}
          {row.percent !== null && !row.limit ? ` · ${row.percent}%` : ""}
          {row.limit ? ` · ${t.nutrientsKeepUnder}` : ""}
        </Text>
      </View>
      <View style={styles.track}>
        <View
          style={[
            styles.fill,
            {
              width: `${Math.round(fraction * 100)}%`,
              backgroundColor: row.limit
                ? colors.muted
                : lowest
                  ? colors.accent
                  : colors.brandPrimary,
            },
          ]}
        />
      </View>
    </View>
  );
}

/** Insights: the 7-day average per nutrient, the ones often low, and kitchen items that are good sources. */
export function WeeklyNutrientsCard({ week }: { week: NutrientWeek | null }) {
  const styles = useCard();
  const { colors } = useTheme();
  const { t, lang } = useAuth();
  const [open, setOpen] = useState(false);
  const nameOf = (key: string) => {
    const found = week?.nutrients.find((row) => row.key === key);
    return found ? (lang === "te" ? found.te : found.en) : key;
  };
  const rows: Row[] = (week?.nutrients || []).map((item) => ({
    key: item.key,
    en: item.en,
    te: item.te,
    unit: item.unit,
    value: item.average,
    reference: item.reference,
    percent: item.percent,
    limit: item.limit,
  }));
  return (
    <View style={styles.card} testID="nutrients-week-card">
      <View style={styles.head}>
        <AppIcon name="sparkles" color={colors.accent} size={18} />
        <Text style={styles.title}>{t.nutrientsWeekTitle}</Text>
      </View>
      {!week || week.days_logged === 0 ? (
        <Text style={styles.sub} testID="nutrients-week-empty">
          {t.nutrientsWeekEmpty}
        </Text>
      ) : (
        <>
          <Text style={styles.sub}>
            {t.nutrientsDays.replace("{n}", String(week.days_logged))}
          </Text>
          {week.often_low.length ? (
            <View style={{ gap: 8 }} testID="nutrients-often-low">
              <Text style={styles.label}>{t.nutrientsOftenLow}</Text>
              <View style={styles.chipWrap}>
                {week.often_low.map((key) => (
                  <View key={key} style={styles.chip}>
                    <Text style={styles.chipText}>{nameOf(key)}</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : (
            <Text style={styles.text}>{t.nutrientsWeekOk}</Text>
          )}
          {week.suggestions.length ? (
            <View style={{ gap: 6 }} testID="nutrients-kitchen">
              <Text style={styles.label}>{t.nutrientsFromKitchen}</Text>
              {week.suggestions.map((item) => (
                <Text key={item.nutrient} style={styles.text}>
                  {nameOf(item.nutrient)}:{" "}
                  {item.items
                    .map((entry) =>
                      lang === "te" && entry.te ? entry.te : entry.name,
                    )
                    .join(", ")}
                </Text>
              ))}
            </View>
          ) : null}
          <Pressable
            testID="nutrients-week-toggle"
            accessibilityRole="button"
            accessibilityState={{ expanded: open }}
            onPress={() => setOpen(!open)}
            style={styles.toggle}
          >
            <Text style={styles.toggleText}>
              {open ? t.nutrientsHide : t.nutrientsShowAll}
            </Text>
            <AppIcon
              name={open ? "up" : "down"}
              color={colors.brandPrimary}
              size={16}
            />
          </Pressable>
          {open ? (
            <View style={styles.list}>
              {rows.map((row) => (
                <NutrientRow
                  key={row.key}
                  row={row}
                  lang={lang}
                  lowest={week.often_low.includes(row.key)}
                />
              ))}
            </View>
          ) : null}
          <Text style={styles.sub}>{t.nutrientsNote}</Text>
        </>
      )}
    </View>
  );
}
