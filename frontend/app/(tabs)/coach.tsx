import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { post } from "@/src/api";
import { AppIcon, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";

// Coach replies can contain markdown; flatten it for clean bubble rendering.
const cleanMarkdown = (text: string) =>
  text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`/g, "")
    .replace(/^#+\s*/gm, "")
    .replace(/^\s*\|/gm, "")
    .replace(/\|/g, " · ");

export default function CoachScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { lang, t } = useAuth();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([
    { role: "coach", text: lang === "te" ? "నమస్కారం. ఈ రోజు మీ ఆరోగ్య ప్రయాణంలో నేను మీతోనే ఉన్నాను." : "Hello. I’m here to make today’s wellness choices feel simpler." },
  ]);

  const send = async (text = input) => {
    if (!text.trim()) return;
    setInput("");
    setMessages((items) => [...items, { role: "user", text }]);
    setBusy(true);
    try {
      const result = await post<{ reply: string }>("/coach", { message: text, language: lang });
      setMessages((items) => [...items, { role: "coach", text: result.reply }]);
    } catch {
      setMessages((items) => [...items, { role: "coach", text: "I’m having trouble connecting. You can still lean on the plate guide: vegetables, protein, whole grains and water." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[styles.root, { paddingTop: insets.top }]} testID="coach-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>NUTRIMITRA AI</Text>
          <Text style={styles.headerTitle}>{t.coach}</Text>
        </View>
        <Pressable testID="coach-photo-button" accessibilityLabel={t.photo} onPress={() => router.push("/log-food")} style={styles.iconButton}>
          <AppIcon name="camera.fill" color={colors.brandPrimary} size={20} />
        </Pressable>
      </View>
      <KeyboardAvoidingView behavior="translate-with-padding" style={styles.flex}>
        <ScrollView contentContainerStyle={styles.chatContent} keyboardShouldPersistTaps="handled">
          {messages.map((message, index) => (
            <View key={`${message.role}-${index}`} style={message.role === "user" ? styles.userBubble : styles.coachBubble} testID={`chat-message-${index}`}>
              <Text style={message.role === "user" ? styles.userBubbleText : styles.coachBubbleText}>{cleanMarkdown(message.text)}</Text>
            </View>
          ))}
          <Text style={styles.fieldLabel}>{t.quick}</Text>
          <View style={styles.quickRow}>
            <Chip label="Easy protein ideas" selected={false} onPress={() => send("Give me an easy high-protein Indian meal idea.")} />
            <Chip label="I feel low energy" selected={false} onPress={() => send("I feel low energy today. What gentle steps can I take?")} />
          </View>
        </ScrollView>
        <View style={styles.chatComposer}>
          <TextInput testID="coach-input" value={input} onChangeText={setInput} placeholder={t.ask} placeholderTextColor={styles.placeholder.color as string} style={styles.chatInput} onSubmitEditing={() => send()} returnKeyType="send" />
          <Pressable testID="coach-send-button" accessibilityLabel={t.send} onPress={() => send()} disabled={busy} style={[styles.sendButton, busy && styles.disabled]}>
            <AppIcon name="arrow.up" color={styles.sendIcon.color as string} size={19} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}
