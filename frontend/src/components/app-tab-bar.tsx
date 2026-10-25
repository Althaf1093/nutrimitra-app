import { useRouter, type Tabs } from "expo-router";
import type { ComponentProps } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { AppIcon } from "@/src/components/icon";
import { Avatar } from "@/src/components/kit";
import { useAuth } from "@/src/context/auth";
import { useBreakpoint } from "@/src/lib/use-breakpoint";
import { layout, makeStyles, radius, useTheme } from "@/src/theme";

type TabBarProps = Parameters<NonNullable<ComponentProps<typeof Tabs>["tabBar"]>>[0];

const useBar = makeStyles((colors) => ({
  bar: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-around", backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10, paddingHorizontal: 8 },
  item: { minWidth: 64, minHeight: 56, alignItems: "center", gap: 4 },
  pill: { width: 52, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  pillOn: { backgroundColor: colors.brandSoft },
  label: { color: colors.muted, fontSize: 11, lineHeight: 15, fontWeight: "600", textAlign: "center" },
  labelOn: { color: colors.brandPrimary, fontWeight: "700" },

  sidebar: { width: layout.sidebar, backgroundColor: colors.card, borderRightWidth: 1, borderRightColor: colors.border, paddingVertical: 28, paddingHorizontal: 18, gap: 6 },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 10, paddingBottom: 22 },
  brandMark: { width: 40, height: 40, borderRadius: 13, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  brandName: { color: colors.onSurface, fontSize: 21, lineHeight: 28, fontWeight: "800", letterSpacing: -0.4 },
  navItem: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 48, paddingHorizontal: 14, borderRadius: radius.md },
  navItemOn: { backgroundColor: colors.brandSoft },
  navText: { color: colors.muted, fontSize: 15, lineHeight: 21, fontWeight: "600", flexShrink: 1 },
  navTextOn: { color: colors.brandPrimary, fontWeight: "700" },
  spacer: { flex: 1 },
  userCard: { flexDirection: "row", alignItems: "center", gap: 12, padding: 12, borderRadius: 16, backgroundColor: colors.brandFaint },
  userName: { color: colors.onSurface, fontSize: 14, lineHeight: 20, fontWeight: "700" },
  userMeta: { color: colors.muted, fontSize: 12, lineHeight: 17 },
}));

// The route names of the four tabs, in order, and the icon each uses.
const TAB_ICONS: Record<string, string> = { index: "today", plan: "plan", coach: "coach", progress: "progress" };

/** The app's navigation: a bottom bar with a pill under the active icon on phones and tablets, a left sidebar on a wide screen. */
export function AppTabBar({ state, descriptors, navigation }: TabBarProps) {
  const styles = useBar();
  const { colors } = useTheme();
  const { isDesktop } = useBreakpoint();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { t, user, profile } = useAuth();

  const tabs = state.routes.map((route, index) => {
    const { options } = descriptors[route.key];
    const focused = state.index === index;
    const label = typeof options.title === "string" ? options.title : route.name;
    const press = () => {
      const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
      if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
    };
    return { key: route.key, name: route.name, label, focused, press, icon: TAB_ICONS[route.name] ?? "default", testID: options.tabBarButtonTestID };
  });

  if (isDesktop) {
    const goal = typeof profile?.wellness_goal === "string" ? profile.wellness_goal : "";
    return (
      <View testID="sidebar" style={styles.sidebar}>
        <View style={styles.brandRow}>
          <View style={styles.brandMark}>
            <AppIcon name="activity" color={colors.onBrandPrimary} size={22} strokeWidth={2.2} />
          </View>
          <Text style={styles.brandName}>Wellstride</Text>
        </View>
        {tabs.map((tab) => (
          <Pressable key={tab.key} testID={`nav-${tab.name}`} accessibilityRole="tab" accessibilityState={{ selected: tab.focused }} accessibilityLabel={tab.label} onPress={tab.press} style={({ pressed }) => [styles.navItem, tab.focused && styles.navItemOn, pressed && { opacity: 0.8 }]}>
            <AppIcon name={tab.icon} size={22} color={tab.focused ? colors.brandPrimary : colors.muted} strokeWidth={tab.focused ? 2.2 : 1.9} />
            <Text style={[styles.navText, tab.focused && styles.navTextOn]}>{tab.label}</Text>
          </Pressable>
        ))}
        <Pressable testID="nav-kitchen" accessibilityRole="button" accessibilityLabel={t.settingsKitchen} onPress={() => router.push("/kitchen")} style={({ pressed }) => [styles.navItem, pressed && { opacity: 0.8 }]}>
          <AppIcon name="kitchen" size={22} color={colors.muted} />
          <Text style={styles.navText}>{t.settingsKitchen}</Text>
        </Pressable>
        <Pressable testID="nav-settings" accessibilityRole="button" accessibilityLabel={t.settings} onPress={() => router.push("/settings")} style={({ pressed }) => [styles.navItem, pressed && { opacity: 0.8 }]}>
          <AppIcon name="settings" size={22} color={colors.muted} />
          <Text style={styles.navText}>{t.settings}</Text>
        </Pressable>
        <View style={styles.spacer} />
        <View style={styles.userCard}>
          <Avatar name={user?.name || user?.email || "?"} size={40} />
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text numberOfLines={1} style={styles.userName}>
              {user?.name || user?.email}
            </Text>
            {goal ? (
              <Text numberOfLines={1} style={styles.userMeta}>
                {goal}
              </Text>
            ) : null}
          </View>
        </View>
      </View>
    );
  }

  return (
    <View testID="tab-bar" style={[styles.bar, { height: 64 + Math.max(insets.bottom, 8), paddingBottom: Math.max(insets.bottom, 8) }]}>
      {tabs.map((tab) => (
        <Pressable key={tab.key} testID={tab.testID ?? `tab-${tab.name}`} accessibilityRole="tab" accessibilityState={{ selected: tab.focused }} accessibilityLabel={tab.label} onPress={tab.press} style={styles.item}>
          <View style={[styles.pill, tab.focused && styles.pillOn]}>
            <AppIcon name={tab.icon} size={22} color={tab.focused ? colors.brandPrimary : colors.muted} strokeWidth={tab.focused ? 2.2 : 1.9} />
          </View>
          <Text style={[styles.label, tab.focused && styles.labelOn]}>{tab.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}
