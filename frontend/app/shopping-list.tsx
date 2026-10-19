import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { AppIcon } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import type { Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { ShoppingItem, ShoppingList } from "@/src/types";

const GROUP_LABELS: Record<string, keyof Copy> = {
  vegetables: "groupVegetables",
  leafy: "groupLeafy",
  staples: "groupStaples",
  pulses: "groupPulses",
  protein: "groupProtein",
  dairy: "groupDairy",
  fruits: "groupFruits",
  oils: "groupOils",
  extras: "groupExtras",
};

// The week's plan minus what is already in the kitchen, grouped like the aisles of a shop.
export default function ShoppingListScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { lang, t, status } = useAuth();
  const [list, setList] = useState<ShoppingList | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (status !== "ready") return;
    api<ShoppingList>("/plan/shopping-list")
      .then(setList)
      .catch(() => setFailed(true));
  }, [status]);

  if (status === "loading") {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }
  if (status !== "ready") {
    return <Redirect href={status === "consent" ? "/consent" : status === "onboarding" ? "/onboarding" : "/welcome"} />;
  }

  const label = (item: ShoppingItem) => (lang === "te" && item.te ? item.te : item.name.split("(")[0].trim());
  const groups = (items: ShoppingItem[]) => {
    const order: string[] = [];
    for (const item of items) if (!order.includes(item.group)) order.push(item.group);
    return order.map((group) => ({ group, items: items.filter((item) => item.group === group) }));
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="shopping-list-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>{t.shoppingEyebrow.toUpperCase()}</Text>
          <Text style={styles.headerTitle}>{t.shoppingList}</Text>
        </View>
        <Pressable testID="shopping-list-close" accessibilityRole="button" accessibilityLabel={t.close} onPress={() => router.back()} style={styles.iconButton}>
          <AppIcon name="xmark" color={colors.onSurface} size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
        {!list && !failed ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 24 }} /> : null}
        {failed ? (
          <View style={styles.reasonCard} testID="shopping-failed">
            <Text style={styles.reasonText}>{t.couldNotLoad}</Text>
          </View>
        ) : null}
        {list && !list.kitchen_based ? (
          <View style={styles.reasonCard} testID="shopping-no-kitchen">
            <Text style={styles.reasonText}>{t.shoppingNoKitchen}</Text>
          </View>
        ) : null}
        {list?.kitchen_based ? (
          <View>
            <Text style={styles.mutedText} testID="shopping-for">
              {t.shoppingFor} {list.household_size}
            </Text>
            <Text style={[styles.sectionTitleSmall, { marginTop: 18 }]}>{t.shoppingToBuy}</Text>
            {list.to_buy.length === 0 ? (
              <View style={styles.reasonCard} testID="shopping-empty">
                <Text style={styles.reasonText}>{t.shoppingEmpty}</Text>
              </View>
            ) : (
              <View testID="shopping-to-buy">
                {groups(list.to_buy).map(({ group, items }) => (
                  <View key={group}>
                    <Text style={[styles.fieldLabel, { marginTop: 14 }]}>{GROUP_LABELS[group] ? (t[GROUP_LABELS[group]] as string) : group}</Text>
                    {items.map((item) => (
                      <View key={item.id} style={styles.foodRow} testID={`shopping-row-${item.id}`}>
                        <Text style={[styles.foodName, styles.flex]}>{label(item)}</Text>
                        <Text style={styles.mutedText}>
                          {item.meals} {t.mealsWord}
                        </Text>
                      </View>
                    ))}
                  </View>
                ))}
              </View>
            )}
            {list.have.length ? (
              <View testID="shopping-have">
                <Text style={[styles.sectionTitleSmall, { marginTop: 26 }]}>{t.shoppingHave}</Text>
                <Text style={[styles.mutedText, { marginTop: 6 }]}>{list.have.map(label).join(", ")}</Text>
              </View>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}
