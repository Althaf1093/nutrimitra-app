import { Redirect, Tabs } from "expo-router";
import { NativeTabs } from "expo-router/unstable-native-tabs";
import { ActivityIndicator, Platform, View } from "react-native";

import { AppIcon } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useTheme } from "@/src/theme";

// iOS 26+ gets native liquid-glass tabs; older iOS, Android and web use the
// classic JS tab bar styled with the theme tokens.
const useNativeTabs = Platform.OS === "ios" && parseInt(String(Platform.Version), 10) >= 26;

export default function TabsLayout() {
  const { t, status } = useAuth();
  const { colors } = useTheme();

  // Route guard: deep links must never render authenticated content.
  if (status === "loading") {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface }}>
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }
  if (status !== "ready") {
    return <Redirect href={status === "onboarding" ? "/onboarding" : "/welcome"} />;
  }

  if (useNativeTabs) {
    return (
      <NativeTabs>
        <NativeTabs.Trigger name="index">
          <NativeTabs.Trigger.Label>{t.today}</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon sf="sun.max.fill" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="plan">
          <NativeTabs.Trigger.Label>{t.plan}</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon sf="list.bullet.clipboard" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="coach">
          <NativeTabs.Trigger.Label>{t.coach}</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon sf="bubble.left.and.bubble.right.fill" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="progress">
          <NativeTabs.Trigger.Label>{t.progress}</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon sf="chart.line.uptrend.xyaxis" />
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
