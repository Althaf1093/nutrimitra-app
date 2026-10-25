import { SymbolView } from "expo-symbols";
import { ColorValue, Pressable, Text, TextInput, View } from "react-native";

import { useAuth } from "@/src/context/auth";
import { mealTypeLabel } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Meal } from "@/src/types";

// SF Symbols only draw on iOS; on the web and Android the same name falls back to a plain glyph so no icon is blank.
const GLYPHS: Record<string, string> = {
  xmark: "✕",
  checkmark: "✓",
  "chevron.right": "›",
  "arrow.clockwise": "↻",
  "arrow.up": "↑",
  "camera.fill": "📷",
  "sun.max.fill": "☀",
  "list.bullet.clipboard": "☰",
  "chart.line.uptrend.xyaxis": "↗",
  "bubble.left.and.bubble.right.fill": "💬",
  sparkles: "✦",
  "leaf.fill": "🌿",
  "heart.text.square.fill": "♥",
  gearshape: "⚙",
  "gearshape.fill": "⚙",
  "figure.walk": "🚶",
};

export function AppIcon({ name, color, size = 22 }: { name: string; color: ColorValue; size?: number }) {
  const glyph = (
    <Text allowFontScaling={false} style={{ color, fontSize: Math.round(size * 0.85), lineHeight: size, width: size, textAlign: "center" }}>
      {GLYPHS[name] ?? "•"}
    </Text>
  );
  return (
    <View testID={`icon-${name}`} accessibilityRole="image" style={{ width: size, height: size }}>
      <SymbolView name={name as never} tintColor={color} size={size} fallback={glyph} />
    </View>
  );
}

export function Button({ label, onPress, secondary = false, disabled = false, testID }: { label: string; onPress: () => void; secondary?: boolean; disabled?: boolean; testID?: string }) {
  const styles = useStyles();
  return (
    <Pressable
      testID={testID || `button-${label.toLowerCase().replace(/\s+/g, "-")}`}
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.button, secondary && styles.buttonSecondary, pressed && styles.pressed, disabled && styles.disabled]}
    >
      <Text style={secondary ? styles.buttonSecondaryText : styles.buttonText}>{label}</Text>
    </Pressable>
  );
}

// `label` identifies the chip (and its testID); `text` is what is shown when it should differ, e.g. a translation.
export function Chip({ label, text, selected, onPress }: { label: string; text?: string; selected: boolean; onPress: () => void }) {
  const styles = useStyles();
  return (
    <Pressable
      testID={`chip-${label.toLowerCase().replace(/\s+/g, "-")}`}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.chip, selected && styles.chipSelected, pressed && styles.pressed]}
    >
      <Text style={selected ? styles.chipSelectedText : styles.chipText}>{text ?? label}</Text>
    </Pressable>
  );
}

export function Field({ label, value, onChangeText, placeholder, secureTextEntry = false, keyboardType = "default" }: { label: string; value: string; onChangeText: (value: string) => void; placeholder?: string; secureTextEntry?: boolean; keyboardType?: "default" | "numeric" }) {
  const { colors } = useTheme();
  const styles = useStyles();
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        testID={`field-${label.toLowerCase().replace(/\s+/g, "-")}`}
        accessibilityLabel={label}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        style={styles.input}
      />
    </View>
  );
}

export function MealCard({ meal, onLog, onSwap, onAteOther, hideLog }: { meal: Meal; onLog?: () => void; onSwap?: () => void; onAteOther?: () => void; hideLog?: boolean }) {
  const styles = useStyles();
  const { lang, t } = useAuth();
  const { colors } = useTheme();
  const title = lang === "te" && meal.te ? meal.te : meal.name;
  // What the meal is made of; a bought-for ingredient is marked, so the plan never hides what is missing.
  const uses = (meal.uses ?? [])
    .slice(0, 6)
    .map((item) => `${lang === "te" && item.te ? item.te : item.name.split("(")[0].trim()}${item.have ? "" : ` (${t.buyWord})`}`)
    .join(", ");
  return (
    <View style={styles.mealCard} testID={`meal-card-${meal.type}`}>
      <View style={styles.mealDot}>
        <AppIcon name={meal.type === "breakfast" ? "sunrise.fill" : meal.type === "dinner" ? "moon.stars.fill" : "circle.grid.2x2.fill"} color={colors.brandPrimary} size={18} />
      </View>
      <View style={styles.flex}>
        <Text style={styles.mealType}>{mealTypeLabel(t, meal.type).toUpperCase()}</Text>
        <Text style={styles.mealName}>{title}</Text>
        <Text style={styles.mealMeta}>
          {meal.portion} · {meal.calories} kcal · {meal.protein_g}g {t.proteinWord}
        </Text>
        {uses ? (
          <Text style={styles.mealMeta} testID={`meal-uses-${meal.type}`}>
            {t.usesWord}: {uses}
          </Text>
        ) : null}
        {meal.ate_other && !meal.logged ? (
          <Text style={[styles.mealMeta, { fontStyle: "italic" }]} testID={`meal-ate-other-${meal.type}`}>
            {t.ateOther}
          </Text>
        ) : null}
        {!meal.logged && (onSwap || onAteOther) ? (
          <View style={{ flexDirection: "row", flexWrap: "wrap", columnGap: 18, marginTop: 8 }}>
            {onSwap ? (
              <Pressable testID={`swap-meal-${meal.type}`} accessibilityRole="button" accessibilityLabel={`${t.swapMeal} ${mealTypeLabel(t, meal.type)}`} hitSlop={8} onPress={onSwap}>
                <Text style={styles.linkText}>{t.swapMeal}</Text>
              </Pressable>
            ) : null}
            {onAteOther ? (
              <Pressable testID={`ate-else-${meal.type}`} accessibilityRole="button" accessibilityLabel={`${t.ateElse} (${mealTypeLabel(t, meal.type)})`} hitSlop={8} onPress={onAteOther}>
                <Text style={styles.linkText}>{t.ateElse}</Text>
              </Pressable>
            ) : null}
          </View>
        ) : null}
      </View>
      {hideLog ? null : meal.logged ? (
        <View testID={`meal-logged-${meal.type}`} accessibilityLabel={`${mealTypeLabel(t, meal.type)} ✓`} style={[styles.logButton, styles.logButtonDone]}>
          <AppIcon name="checkmark" color={colors.onBrandPrimary} size={18} />
        </View>
      ) : (
        <Pressable testID={`log-meal-${meal.type}`} accessibilityRole="button" accessibilityLabel={`${t.log} ${mealTypeLabel(t, meal.type)}`} onPress={onLog} style={styles.logButton}>
          <Text style={styles.logButtonText}>+</Text>
        </Pressable>
      )}
    </View>
  );
}
