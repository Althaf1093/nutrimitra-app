import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { AppIcon, Button, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

export default function WelcomeScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { lang, setLang, t, signInEmail, signInGoogle, status } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Signed-in users (including returning Google OAuth sessions) never sit on
  // the auth screen — send them straight into the app.
  if (status === "ready") return <Redirect href="/(tabs)" />;
  if (status === "onboarding") return <Redirect href="/onboarding" />;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await signInEmail(mode, email, password, name);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again");
    } finally {
      setBusy(false);
    }
  };

  const google = async () => {
    setBusy(true);
    setError("");
    try {
      await signInGoogle();
    } catch {
      setError("Google sign-in was interrupted. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="welcome-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
        <View style={styles.brandMark}>
          <AppIcon name="leaf.fill" color={styles.brandIcon.color as string} size={28} />
        </View>
        <Pressable testID="language-toggle" onPress={() => setLang(lang === "en" ? "te" : "en")} style={styles.languagePill}>
          <Text style={styles.languageText}>{lang === "en" ? "తెలుగు" : "English"}</Text>
        </Pressable>
        <Text style={styles.eyebrow}>NUTRIMITRA · INDIA</Text>
        <Text style={styles.heroTitle}>{t.welcome}</Text>
        <Text style={styles.heroSub}>{t.welcomeSub}</Text>
        <View style={styles.authCard}>
          <View style={styles.authTabs}>
            <Pressable testID="auth-tab-signin" onPress={() => setMode("signin")} style={[styles.authTab, mode === "signin" && styles.authTabActive]}>
              <Text style={mode === "signin" ? styles.authTabActiveText : styles.authTabText}>{t.signIn}</Text>
            </Pressable>
            <Pressable testID="auth-tab-signup" onPress={() => setMode("signup")} style={[styles.authTab, mode === "signup" && styles.authTabActive]}>
              <Text style={mode === "signup" ? styles.authTabActiveText : styles.authTabText}>{t.create}</Text>
            </Pressable>
          </View>
          {mode === "signup" && <Field label={t.name} value={name} onChangeText={setName} />}
          <Field label={t.email} value={email} onChangeText={setEmail} />
          <Field label={t.password} value={password} onChangeText={setPassword} secureTextEntry />
          {error ? <Text style={styles.errorText} testID="auth-error">{error}</Text> : null}
          <Button testID="auth-submit-button" label={busy ? "..." : mode === "signin" ? t.signIn : t.create} onPress={submit} disabled={busy || !email || password.length < 8} />
          <Button testID="google-signin-button" label={t.welcomeGoogle} onPress={google} secondary disabled={busy} />
          <Text style={styles.authHint}>
            {mode === "signin" ? t.noAccount : t.already}{" "}
            <Text style={styles.linkText} onPress={() => setMode(mode === "signin" ? "signup" : "signin")}>
              {mode === "signin" ? t.create : t.signIn}
            </Text>
          </Text>
        </View>
        <Text style={styles.safeNote}>Private by design · Your wellness data stays yours.</Text>
      </KeyboardAwareScrollView>
    </View>
  );
}
