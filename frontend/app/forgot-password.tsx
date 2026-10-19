import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { post } from "@/src/api";
import { Button, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

// Step 1 of resetting a password: ask for a code. The answer is the same whether or not the email has an account.
export default function ForgotPasswordScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { t } = useAuth();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = async () => {
    setBusy(true);
    setError("");
    try {
      await post("/auth/forgot-password", { email: email.trim() });
      router.push({ pathname: "/reset-password", params: { email: email.trim() } });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="forgot-password-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>WELLSTRIDE</Text>
        <Text style={styles.heroTitle}>{t.forgotTitle}</Text>
        <Text style={styles.heroSub}>{t.forgotSub}</Text>
        <View style={styles.authCard}>
          <Field label={t.email} value={email} onChangeText={setEmail} />
          {error ? <Text style={styles.errorText} testID="forgot-error">{error}</Text> : null}
          <Button testID="forgot-send-button" label={busy ? "..." : t.sendCode} onPress={send} disabled={busy || !email.includes("@")} />
          <Button testID="forgot-have-code-button" label={t.haveCode} secondary onPress={() => router.push({ pathname: "/reset-password", params: { email: email.trim() } })} />
          <Text style={styles.authHint}>
            <Text style={styles.linkText} onPress={() => router.back()} testID="forgot-back-link">
              {t.backToSignIn}
            </Text>
          </Text>
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
