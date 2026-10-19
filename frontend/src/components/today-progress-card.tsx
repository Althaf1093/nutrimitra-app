import { Text, View } from "react-native";

import type { useStyles } from "@/src/styles";
import type { Copy } from "@/src/i18n";
import type { Dashboard } from "@/src/types";

// Plain counts of what the user logged today against their estimated calorie target.
// Deliberately not a score: nothing here is measured health data.
export function TodayProgressCard({ dashboard, t, styles }: { dashboard: Dashboard | null; t: Copy; styles: ReturnType<typeof useStyles> }) {
  const eaten = dashboard?.calories || 0;
  const target = dashboard?.target_calories || 0;
  return (
    <View style={styles.readinessCard} testID="today-progress-card">
      <View style={styles.flex}>
        <Text style={styles.cardEyebrowOnDark}>{t.todayProgress.toUpperCase()}</Text>
        <Text style={styles.readinessValue} testID="today-progress-calories">
          {eaten}
          <Text style={styles.readinessSlash}>
            {" "}
            / {target} kcal
          </Text>
        </Text>
        <Text style={styles.cardCaption}>{t.todayProgressSub}</Text>
      </View>
      <View style={styles.readinessRing}>
        <Text style={styles.ringText} testID="today-progress-minutes">
          {dashboard?.activity_minutes || 0}
        </Text>
        <Text style={styles.ringCaption}>{t.activeWord} {t.minutes}</Text>
      </View>
    </View>
  );
}
