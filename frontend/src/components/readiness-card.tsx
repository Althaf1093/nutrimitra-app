import { Text, View } from "react-native";

import type { useStyles } from "@/src/styles";
import type { Copy } from "@/src/i18n";
import type { Dashboard } from "@/src/types";

export function ReadinessCard({ dashboard, t, styles }: { dashboard: Dashboard | null; t: Copy; styles: ReturnType<typeof useStyles> }) {
  return (
    <View style={styles.readinessCard} testID="readiness-card">
      <View style={styles.flex}>
        <Text style={styles.cardEyebrowOnDark}>{t.ready.toUpperCase()}</Text>
        <Text style={styles.readinessValue}>
          {dashboard?.readiness || 64}
          <Text style={styles.readinessSlash}> / 100</Text>
        </Text>
        <Text style={styles.cardCaption}>A steady start is enough.</Text>
      </View>
      <View style={styles.readinessRing}>
        <Text style={styles.ringText}>{dashboard?.active_calories || 0}</Text>
        <Text style={styles.ringCaption}>active kcal</Text>
      </View>
    </View>
  );
}
