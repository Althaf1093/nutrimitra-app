import { Text, View } from "react-native";

import { ProgressRing } from "@/src/components/kit";
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
  note: { color: colors.onHero, opacity: 0.8, fontSize: 12, lineHeight: 17 },
}));

// Plain counts of what the user logged today against their estimated calorie target, in a green summary card with a ring.
// Deliberately not a score: nothing here is measured health data.
export function TodayProgressCard({ dashboard, t }: { dashboard: Dashboard | null; t: Copy }) {
  const styles = useCard();
  const eaten = Math.round(dashboard?.calories || 0);
  const target = Math.round(dashboard?.target_calories || 0);
  const left = Math.max(0, target - eaten);
  const minutes = dashboard?.activity_minutes || 0;
  const burned = Math.round(dashboard?.active_calories || 0);
  return (
    <View style={styles.card} testID="today-progress-card">
      <View style={styles.top}>
        <ProgressRing value={eaten} max={target} size={132} stroke={12}>
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
      <Text style={styles.note}>{t.todayProgressSub}</Text>
    </View>
  );
}
