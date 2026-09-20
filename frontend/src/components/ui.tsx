import { SymbolView } from "expo-symbols";
import { ColorValue, Pressable, Text, TextInput, View } from "react-native";

import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Meal } from "@/src/types";

export function AppIcon({ name, color, size = 22 }: { name: string; color: ColorValue; size?: number }) {
  return (
    <View testID={`icon-${name}`} accessibilityRole="image" style={{ width: size, height: size }}>
      <SymbolView name={name as never} tintColor={color} size={size} />
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

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const styles = useStyles();
  return (
    <Pressable
      testID={`chip-${label.toLowerCase().replace(/\s+/g, "-")}`}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.chip, selected && styles.chipSelected, pressed && styles.pressed]}
    >
      <Text style={selected ? styles.chipSelectedText : styles.chipText}>{label}</Text>
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

export function MealCard({ meal, onLog }: { meal: Meal; onLog: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.mealCard} testID={`meal-card-${meal.type}`}>
      <View style={styles.mealDot}>
        <AppIcon name={meal.type === "breakfast" ? "sunrise.fill" : meal.type === "dinner" ? "moon.stars.fill" : "circle.grid.2x2.fill"} color={colors.brandPrimary} size={18} />
      </View>
      <View style={styles.flex}>
        <Text style={styles.mealType}>{meal.type.toUpperCase()}</Text>
        <Text style={styles.mealName}>{meal.name}</Text>
        <Text style={styles.mealMeta}>
          {meal.portion} · {meal.calories} kcal · {meal.protein_g}g protein
        </Text>
      </View>
      <Pressable testID={`log-meal-${meal.type}`} accessibilityRole="button" accessibilityLabel={`Log ${meal.type}`} onPress={onLog} style={styles.logButton}>
        <Text style={styles.logButtonText}>+</Text>
      </Pressable>
    </View>
  );
}
