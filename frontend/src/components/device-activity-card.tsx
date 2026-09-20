import { Pressable, Text, View } from "react-native";

import { AppIcon } from "@/src/components/ui";
import type { Copy } from "@/src/i18n";
import type { HealthSummary } from "@/src/lib/health";
import type { useStyles } from "@/src/styles";
import type { ThemeColors } from "@/src/theme";

export function DeviceActivityCard({
  health,
  sleepHours,
  t,
  styles,
  colors,
  syncing,
  onSync,
  onOpenSettings,
}: {
  health: HealthSummary | null;
  sleepHours: number;
  t: Copy;
  styles: ReturnType<typeof useStyles>;
  colors: ThemeColors;
  syncing: boolean;
  onSync: () => void;
  onOpenSettings: () => void;
}) {
  return (
    <View style={[styles.syncCard, { marginBottom: 0 }]} testID="device-activity-card">
      <View style={styles.syncIcon}>
        <AppIcon name="figure.walk" color={styles.syncIconTint.color as string} size={22} />
      </View>
      <View style={styles.flex}>
        {health?.connected ? (
          <>
            <Text style={styles.mealName} testID="device-steps-value">
              {health.steps.toLocaleString()} {t.steps} · {sleepHours}h {t.sleep}
            </Text>
            <Text style={styles.mutedText}>
              {t.deviceMeasured} · {health.records} records today
            </Text>
          </>
        ) : (
          <>
            <Text style={styles.mealName}>{t.deviceActivity}</Text>
            <Text style={styles.mutedText}>{t.enableHealthFirst}</Text>
          </>
        )}
      </View>
      {health?.connected ? (
        <Pressable testID="sync-device-button" accessibilityRole="button" accessibilityLabel={t.deviceSync} disabled={syncing} onPress={onSync} style={({ pressed }) => [styles.iconButton, pressed && styles.pressed, syncing && styles.disabled]}>
          <AppIcon name="arrow.clockwise" color={colors.brandPrimary} size={20} />
        </Pressable>
      ) : (
        <Pressable testID="open-health-settings" accessibilityRole="button" accessibilityLabel={t.settings} onPress={onOpenSettings} style={styles.iconButton}>
          <AppIcon name="gearshape" color={colors.brandPrimary} size={20} />
        </Pressable>
      )}
    </View>
  );
}
