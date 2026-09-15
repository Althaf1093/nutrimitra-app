import { Tabs } from "expo-router";
import { Icon, Label, NativeTabs } from "expo-router/unstable-native-tabs";
import { Platform } from "react-native";

import { AppIcon } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useTheme } from "@/src/theme";

// iOS 26+ gets native liquid-glass tabs; older iOS, Android and web use the
// classic JS tab bar styled with the theme tokens.
const useNativeTabs = Platform.OS === "ios" && parseInt(String(Platform.Version), 10) >= 26;

export default function TabsLayout() {
  const { t } = useAuth();
  const { colors } = useTheme();

  if (useNativeTabs) {
    return (
      <NativeTabs>
        <NativeTabs.Trigger name="index">
          <Label>{t.today}</Label>
          <Icon sf="sun.max.fill" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="plan">
          <Label>{t.plan}</Label>
          <Icon sf="list.bullet.clipboard" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="coach">
          <Label>{t.coach}</Label>
          <Icon sf="bubble.left.and.bubble.right.fill" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="progress">
          <Label>{t.progress}</Label>
          <Icon sf="chart.line.uptrend.xyaxis" />
        </NativeTabs.Trigger>
      </NativeTabs>
    );
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.divider, ...(Platform.OS === "web" ? { height: 64 } : {}) },
        tabBarItemStyle: { alignSelf: "center" },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t.today, tabBarIcon: ({ color }) => <AppIcon name="sun.max.fill" color={color} size={21} /> }} />
      <Tabs.Screen name="plan" options={{ title: t.plan, tabBarIcon: ({ color }) => <AppIcon name="list.bullet.clipboard" color={color} size={21} /> }} />
      <Tabs.Screen name="coach" options={{ title: t.coach, tabBarIcon: ({ color }) => <AppIcon name="bubble.left.and.bubble.right.fill" color={color} size={21} /> }} />
      <Tabs.Screen name="progress" options={{ title: t.progress, tabBarIcon: ({ color }) => <AppIcon name="chart.line.uptrend.xyaxis" color={color} size={21} /> }} />
    </Tabs>
  );
}
