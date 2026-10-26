import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { ApiError } from "@/src/api";
import { ConsentCheckbox, LegalLinks } from "@/src/components/legal-links";
import { SegmentedControl } from "@/src/components/kit";
import { AppIcon, Button, Field } from "@/src/components/ui";
import { WelcomeArt } from "@/src/components/welcome-art";
import { useAuth } from "@/src/context/auth";
import { googleEnabled } from "@/src/lib/google-auth";
import { useBreakpoint } from "@/src/lib/use-breakpoint";
import { useStyles } from "@/src/styles";
import { makeStyles, radius, useTheme } from "@/src/theme";

const useWelcome = makeStyles((colors) => ({
  page: {
    flexGrow: 1,
    width: "100%",
    maxWidth: 1040,
    alignSelf: "center",
    padding: 22,
    paddingTop: 20,
    paddingBottom: 28,
    gap: 18,
  },
  pageWide: {
    flexDirection: "row",
    alignItems: "center",
    gap: 56,
    paddingTop: 48,
  },
  column: { gap: 18 },
  columnWide: { flex: 1 },
  top: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  logo: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  brandName: {
    color: colors.onSurface,
    fontSize: 19,
    fontWeight: "800",
  },
  title: {
    color: colors.onSurface,
    fontSize: 30,
    lineHeight: 40,
    fontWeight: "800",
  },
  tag: { color: colors.brandPrimary, fontSize: 15, fontWeight: "600" },
  sub: { color: colors.muted, fontSize: 14, lineHeight: 22 },
  feature: { flexDirection: "row", alignItems: "center", gap: 12 },
  featureIcon: {
    width: 36,
    height: 36,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
  },
  featureText: {
    flex: 1,
    color: colors.onSurface,
    fontSize: 14,
    fontWeight: "600",
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.xl,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.border,
    boxShadow: colors.shadowCard,
  },
  age: {
    color: colors.muted,
    fontSize: 11,
    lineHeight: 16,
    textAlign: "center",
  },
}));

export default function WelcomeScreen() {
  const styles = useStyles();
  const w = useWelcome();
  const { colors } = useTheme();
  const { isDesktop } = useBreakpoint();
  const router = useRouter();
  const { lang, setLang, t, signInEmail, signInGoogle, status } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accepted, setAccepted] = useState(false);
  // Phones first see two big buttons (as in the design); the form opens once one is chosen. Wide screens keep the form beside the hero.
  const [showForm, setShowForm] = useState(false);
  const formVisible = isDesktop || showForm;
  const openForm = (next: "signin" | "signup") => {
    setMode(next);
    setShowForm(true);
  };

  // Signed-in users never sit on the auth screen — send them straight into the app.
  if (status === "ready") return <Redirect href="/(tabs)" />;
  if (status === "consent") return <Redirect href="/consent" />;
  if (status === "onboarding") return <Redirect href="/onboarding" />;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await signInEmail(mode, email, password, name, accepted);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  const google = async () => {
    setBusy(true);
    setError("");
    try {
      await signInGoogle(accepted);
    } catch (err) {
      // A new Google account needs the box ticked first: show it (it lives on the Create tab) and say why.
      if (err instanceof ApiError && err.code === "consent_required") {
        setMode("signup");
        setError(t.consentRequired);
        return;
      }
      setError(
        err instanceof Error && err.message ? err.message : t.googleFailed,
      );
    } finally {
      setBusy(false);
    }
  };

  const features = [
    {
      icon: "camera",
      text: t.welcomeFeat1,
      bg: colors.brandSoft,
      fg: colors.brandPrimary,
    },
    {
      icon: "kitchen",
      text: t.welcomeFeat2,
      bg: colors.accentSoft,
      fg: colors.accent,
    },
    {
      icon: "progress",
      text: t.welcomeFeat3,
      bg: colors.macroFibreSoft,
      fg: colors.macroFibre,
    },
  ];

  return (
    <View style={styles.root} testID="welcome-screen">
      <KeyboardAwareScrollView
        contentContainerStyle={[w.page, isDesktop && w.pageWide]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[w.column, isDesktop && w.columnWide]}>
          <View style={w.top}>
            <View style={w.brandRow}>
              <View style={w.logo}>
                <AppIcon
                  name="activity"
                  color={colors.onBrandPrimary}
                  size={20}
                />
              </View>
              <Text style={w.brandName}>Wellstride</Text>
            </View>
            <SegmentedControl
              testID="language-toggle"
              value={lang}
              onChange={setLang}
              options={[
                { id: "te", label: "తెలుగు" },
                { id: "en", label: "English" },
              ]}
            />
          </View>
          <WelcomeArt />
          <View style={{ gap: 8 }}>
            <Text style={w.title} accessibilityRole="header">
              {t.welcome}
            </Text>
            <Text style={w.tag}>{t.welcomeTag}</Text>
            <Text style={w.sub}>{t.welcomeSub}</Text>
          </View>
          <View style={{ gap: 10 }}>
            {features.map((feature) => (
              <View key={feature.icon} style={w.feature}>
                <View style={[w.featureIcon, { backgroundColor: feature.bg }]}>
                  <AppIcon name={feature.icon} color={feature.fg} size={20} />
                </View>
                <Text style={w.featureText}>{feature.text}</Text>
              </View>
            ))}
          </View>
        </View>
        <View style={[w.column, isDesktop && w.columnWide]}>
          {!formVisible ? (
            <View style={{ gap: 10 }}>
              <Button
                testID="get-started-button"
                label={t.getStarted}
                onPress={() => openForm("signup")}
              />
              <Button
                testID="have-account-button"
                label={t.haveAccount}
                onPress={() => openForm("signin")}
                secondary
              />
            </View>
          ) : null}
          {formVisible ? (
            <View style={w.card}>
              <View style={styles.authTabs}>
                <Pressable
                  testID="auth-tab-signin"
                  onPress={() => setMode("signin")}
                  style={[
                    styles.authTab,
                    mode === "signin" && styles.authTabActive,
                  ]}
                >
                  <Text
                    style={
                      mode === "signin"
                        ? styles.authTabActiveText
                        : styles.authTabText
                    }
                  >
                    {t.signIn}
                  </Text>
                </Pressable>
                <Pressable
                  testID="auth-tab-signup"
                  onPress={() => setMode("signup")}
                  style={[
                    styles.authTab,
                    mode === "signup" && styles.authTabActive,
                  ]}
                >
                  <Text
                    style={
                      mode === "signup"
                        ? styles.authTabActiveText
                        : styles.authTabText
                    }
                  >
                    {t.create}
                  </Text>
                </Pressable>
              </View>
              {mode === "signup" && (
                <Field label={t.name} value={name} onChangeText={setName} />
              )}
              <Field label={t.email} value={email} onChangeText={setEmail} />
              <Field
                label={t.password}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
              {mode === "signup" ? (
                <ConsentCheckbox checked={accepted} onChange={setAccepted} />
              ) : null}
              {error ? (
                <Text style={styles.errorText} testID="auth-error">
                  {error}
                </Text>
              ) : null}
              <Button
                testID="auth-submit-button"
                label={busy ? "..." : mode === "signin" ? t.signIn : t.create}
                onPress={submit}
                disabled={
                  busy ||
                  !email ||
                  password.length < 8 ||
                  (mode === "signup" && !accepted)
                }
              />
              {mode === "signin" ? (
                <Text
                  testID="forgot-password-link"
                  accessibilityRole="link"
                  style={[styles.linkText, { marginTop: 12 }]}
                  onPress={() => router.push("/forgot-password")}
                >
                  {t.forgotPassword}
                </Text>
              ) : null}
              {googleEnabled ? (
                <Button
                  testID="google-signin-button"
                  label={t.welcomeGoogle}
                  onPress={google}
                  secondary
                  disabled={busy}
                />
              ) : null}
              <Text style={styles.authHint}>
                {mode === "signin" ? t.noAccount : t.already}{" "}
                <Text
                  style={styles.linkText}
                  onPress={() =>
                    setMode(mode === "signin" ? "signup" : "signin")
                  }
                >
                  {mode === "signin" ? t.create : t.signIn}
                </Text>
              </Text>
            </View>
          ) : null}
          <Text style={styles.safeNote}>{t.privacyLine}</Text>
          <LegalLinks />
          <Text style={w.age}>{t.welcomeAge}</Text>
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
