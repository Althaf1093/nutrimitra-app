import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, post } from "@/src/api";
import { AppIcon, Button, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";

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
      <Text style={styles.cardEyebrow}>RECIPE</Text>
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
          <Text style={styles.recipeLabel}>{t.steps.toUpperCase()}</Text>
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
  const [notice, setNotice] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "coach", text: lang === "te" ? "నమస్కారం. ఈ రోజు మీ ఆరోగ్య ప్రయాణంలో నేను మీతోనే ఉన్నాను." : "Hello. I’m here to make today’s wellness choices feel simpler." },
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
    setNotice("");
    setMessages((items) => [...items, { role: "user", text }]);
    setBusy(true);
    try {
      const result = await post<{ reply: string; recipe?: Recipe | null }>("/coach", { message: text, language: lang });
      setMessages((items) => [...items, { role: "coach", text: result.reply, recipe: result.recipe }]);
    } catch {
      setMessages((items) => [...items, { role: "coach", text: "I’m having trouble connecting. You can still lean on the plate guide: vegetables, protein, whole grains and water." }]);
    } finally {
      setBusy(false);
    }
  };

  const logRecipe = async (recipe: Recipe) => {
    try {
      await post("/meals", { meal_type: "snack", name: recipe.name, calories: recipe.calories, protein_g: recipe.protein_g, carbs_g: recipe.carbs_g, fat_g: recipe.fat_g, source: "coach recipe" });
      setNotice(t.addMeal);
    } catch {
      setNotice("Could not log meal");
    }
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="coach-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA AI</Text>
          <Text style={styles.headerTitle}>{t.coach}</Text>
        </View>
        <Pressable testID="coach-photo-button" accessibilityRole="button" accessibilityLabel={t.photo} onPress={() => router.push("/log-food")} style={styles.iconButton}>
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
            <Chip label="Easy protein ideas" selected={false} onPress={() => send("Give me an easy high-protein Indian meal idea.")} />
            <Chip label="Recipe for dinner" selected={false} onPress={() => send("Share a quick healthy Indian dinner recipe I can cook tonight.")} />
            <Chip label="I feel low energy" selected={false} onPress={() => send("I feel low energy today. What gentle steps can I take?")} />
          </View>
        </ScrollView>
        {notice ? (
          <Text style={styles.successText} testID="coach-notice">
            {notice}
          </Text>
        ) : null}
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
