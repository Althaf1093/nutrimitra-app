import { Text, View } from "react-native";

import { MacroBar, ProgressRing } from "@/src/components/kit";
import { useBreakpoint } from "@/src/lib/use-breakpoint";
import type { Copy } from "@/src/i18n";
import { makeStyles, radius, space } from "@/src/theme";
import type { Dashboard } from "@/src/types";

const useCard = makeStyles((colors) => ({
  card: { backgroundColor: colors.hero, borderRadius: radius.xl, padding: 22, gap: space.md, boxShadow: colors.shadowCard },
  top: { flexDirection: "row", alignItems: "center", gap: 20 },
  ringValue: { color: colors.onHero, fontSize: 30, fontWeight: "800", letterSpacing: -0.6, lineHeight: 34, fontVariant: ["tabular-nums"] },
  ringCaption: { color: colors.onHero, opacity: 0.8, fontSize: 12, fontWeight: "600", marginTop: 2 },
  side: { flex: 1, gap: 12 },
  label: { color: colors.onHero, opacity: 0.8, fontSize: 12, fontWeight: "600" },
  value: { color: colors.onHero, fontSize: 20, fontWeight: "800", fontVariant: ["tabular-nums"] },
  valueSub: { color: colors.onHero, opacity: 0.8, fontSize: 13, fontWeight: "600" },
  macros: { flexDirection: "row", gap: 12 },
  note: { color: colors.onHero, opacity: 0.8, fontSize: 12, lineHeight: 17 },
}));

// Plain counts of what the user logged today against their estimated calorie target, in a green summary card with a ring.
// Deliberately not a score: nothing here is measured health data.
export function TodayProgressCard({ dashboard, t }: { dashboard: Dashboard | null; t: Copy }) {
  const styles = useCard();
  const { isDesktop } = useBreakpoint();
  const eaten = Math.round(dashboard?.calories || 0);
  const target = Math.round(dashboard?.target_calories || 0);
  const left = Math.max(0, target - eaten);
  const minutes = dashboard?.activity_minutes || 0;
  const burned = Math.round(dashboard?.active_calories || 0);
  return (
    <View style={styles.card} testID="today-progress-card">
      <View style={styles.top}>
        <ProgressRing value={eaten} max={target} size={isDesktop ? 168 : 132} stroke={12} testID="today-ring">
          <Text style={styles.ringValue} testID="today-progress-left">
            {left}
          </Text>
          <Text style={styles.ringCaption}>{t.kcalLeft}</Text>
        </ProgressRing>
        <View style={styles.side}>
          <View>
            <Text style={styles.label}>{t.eatenWord}</Text>
            <Text style={styles.value} testID="today-progress-calories">
              {eaten}
              <Text style={styles.valueSub}>
                {" "}
                / {target} kcal
              </Text>
            </Text>
          </View>
          <View>
            <Text style={styles.label}>{t.activeLabel}</Text>
            <Text style={styles.value}>
              <Text testID="today-progress-minutes">{minutes}</Text>
              <Text style={styles.valueSub}>
                {" "}
                {t.minutes}
                {burned ? ` · ~${burned} kcal` : ""}
              </Text>
            </Text>
          </View>
        </View>
      </View>
      <View style={styles.macros} testID="today-macros">
        <MacroBar onHero label={t.macroProteinName} value={dashboard?.protein_g || 0} target={dashboard?.target_protein_g || 0} color="#8FD3C0" testID="macro-protein" />
        <MacroBar onHero label={t.macroCarbsName} value={dashboard?.carbs_g || 0} target={dashboard?.target_carbs_g || 0} color="#F2C867" testID="macro-carbs" />
        <MacroBar onHero label={t.macroFatName} value={dashboard?.fat_g || 0} target={dashboard?.target_fat_g || 0} color="#F2A08F" testID="macro-fat" />
        <MacroBar onHero label={t.macroFibreName} value={dashboard?.fibre_g || 0} target={dashboard?.target_fibre_g || 0} color="#BDB1EA" noData={!dashboard?.fibre_tracked} noDataText={t.fibreAddToTrack} testID="macro-fibre" />
      </View>
      <Text style={styles.note}>{t.todayProgressSub}</Text>
    </View>
  );
}
