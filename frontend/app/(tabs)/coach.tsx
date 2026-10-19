import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, del, isAiBusy, post } from "@/src/api";
import { useToast } from "@/src/components/toast";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";

// The chat box sits just above the tab bar; toasts rise above it so they never cover the text field.
const COMPOSER_LIFT = 64;

export type Recipe = {
  name: string;
  time_min: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  ingredients: string[];
  steps: string[];
};

type ChatMessage = { role: string; text: string; recipe?: Recipe | null };

// Coach replies can contain markdown; flatten it for clean bubble rendering.
const cleanMarkdown = (text: string) =>
  text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`/g, "")
    .replace(/^#+\s*/gm, "")
    .replace(/^\s*\|/gm, "")
    .replace(/\|/g, " · ");

function RecipeCard({ recipe, index, t, onLog }: { recipe: Recipe; index: number; t: Copy; onLog: () => void }) {
  const styles = useStyles();
  return (
    <View style={styles.recipeCard} testID={`recipe-card-${index}`}>
      <Text style={styles.cardEyebrow}>{t.recipeCard.toUpperCase()}</Text>
      <Text style={styles.recipeTitle}>{recipe.name}</Text>
      <Text style={styles.mealMeta}>
        {recipe.time_min} {t.minutes} · {recipe.calories} kcal · {recipe.protein_g}g protein
      </Text>
      {recipe.ingredients.length ? (
        <>
          <Text style={styles.recipeLabel}>{t.ingredients.toUpperCase()}</Text>
          {recipe.ingredients.map((item) => (
            <Text key={item} style={styles.recipeItem}>
              · {item}
            </Text>
          ))}
        </>
      ) : null}
      {recipe.steps.length ? (
        <>
          <Text style={styles.recipeLabel}>{t.recipeSteps.toUpperCase()}</Text>
          {recipe.steps.map((step, stepIndex) => (
            <Text key={`${stepIndex}`} style={styles.recipeItem}>
              {stepIndex + 1}. {step}
            </Text>
          ))}
        </>
      ) : null}
      <Button testID={`recipe-log-${index}`} label={t.logRecipe} onPress={onLog} />
    </View>
  );
}

export default function CoachScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { lang, t } = useAuth();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "coach", text: t.coachGreeting },
  ]);

  // Conversation memory: restore previous session (stored only when the user
  // has Coach memory enabled in privacy settings). Reloaded on focus so
  // changes made in Settings apply immediately.
  useFocusEffect(
    useCallback(() => {
      api<{ messages: { role: string; text: string; recipe?: Recipe | null }[] }>("/coach/history")
        .then((result) => {
          if (result.messages?.length) {
            setMessages(result.messages.map((item) => ({ role: item.role, text: item.text, recipe: item.recipe })));
          }
        })
        .catch(() => undefined);
    }, []),
  );

  const send = async (text = input) => {
    if (!text.trim()) return;
    setInput("");
    setMessages((items) => [...items, { role: "user", text }]);
    setBusy(true);
    try {
      const result = await post<{ reply: string; recipe?: Recipe | null }>("/coach", { message: text, language: lang });
      setMessages((items) => [...items, { role: "coach", text: result.reply, recipe: result.recipe }]);
    } catch (err) {
      // Not a coach reply: shown as a notice so it is never mistaken for (or stored as) advice.
      toast.show(isAiBusy(err) ? t.aiBusy : t.aiUnavailable, { type: "error", raise: COMPOSER_LIFT });
    } finally {
      setBusy(false);
    }
  };

  const logRecipe = async (recipe: Recipe) => {
    try {
      const saved = await post<{ id: string }>("/meals", { meal_type: "snack", name: recipe.name, calories: recipe.calories, protein_g: recipe.protein_g, carbs_g: recipe.carbs_g, fat_g: recipe.fat_g, source: "coach recipe" });
      toast.show(t.addMeal, {
        raise: COMPOSER_LIFT,
        actionLabel: t.undo,
        onAction: () =>
          del(`/meals/${saved.id}`)
            .then(() => toast.show(t.undone, { type: "info", raise: COMPOSER_LIFT }))
            .catch(() => toast.show(t.couldNotUndo, { type: "error", raise: COMPOSER_LIFT })),
      });
    } catch {
      toast.show(t.couldNotLogMeal, { type: "error", raise: COMPOSER_LIFT });
    }
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="coach-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>WELLSTRIDE AI</Text>
          <Text style={styles.headerTitle}>{t.coach}</Text>
        </View>
        <Pressable testID="coach-photo-button" accessibilityRole="button" accessibilityLabel={t.photo} onPress={() => router.push({ pathname: "/log-food", params: { mode: "photo" } })} style={styles.iconButton}>
          <AppIcon name="camera.fill" color={colors.brandPrimary} size={20} />
        </Pressable>
      </View>
      <KeyboardAvoidingView behavior="translate-with-padding" style={styles.flex}>
        <ScrollView contentContainerStyle={styles.chatContent} keyboardShouldPersistTaps="handled">
          {messages.map((message, index) => (
            <View key={`${message.role}-${index}`}>
              <View style={message.role === "user" ? styles.userBubble : styles.coachBubble} testID={`chat-message-${index}`}>
                <Text style={message.role === "user" ? styles.userBubbleText : styles.coachBubbleText}>{cleanMarkdown(message.text)}</Text>
              </View>
              {message.recipe ? <RecipeCard recipe={message.recipe} index={index} t={t} onLog={() => logRecipe(message.recipe as Recipe)} /> : null}
            </View>
          ))}
          <Text style={styles.fieldLabel}>{t.quick}</Text>
          <View style={styles.quickRow}>
            <Chip label={t.quickProtein} selected={false} onPress={() => send(t.quickProteinPrompt)} />
            <Chip label={t.quickDinner} selected={false} onPress={() => send(t.quickDinnerPrompt)} />
            <Chip label={t.quickLowEnergy} selected={false} onPress={() => send(t.quickLowEnergyPrompt)} />
          </View>
        </ScrollView>
        <Text style={styles.wellnessNotice} testID="coach-wellness-notice">
          {t.wellnessNotice}
        </Text>
        <View style={styles.chatComposer}>
          <TextInput testID="coach-input" value={input} onChangeText={setInput} placeholder={t.ask} placeholderTextColor={styles.placeholder.color as string} style={styles.chatInput} onSubmitEditing={() => send()} returnKeyType="send" />
          <Pressable testID="coach-send-button" accessibilityRole="button" accessibilityLabel={t.send} onPress={() => send()} disabled={busy} style={[styles.sendButton, busy && styles.disabled]}>
            <AppIcon name="arrow.up" color={styles.sendIcon.color as string} size={19} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}
