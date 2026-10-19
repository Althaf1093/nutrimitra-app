import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { post } from "@/src/api";
import { Button, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

// Step 2: the code from the email and a new password. The email link (wellstride://reset-password?email=..&code=..) opens
// this screen with both filled in.
export default function ResetPasswordScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { t } = useAuth();
  const params = useLocalSearchParams<{ email?: string; code?: string }>();
  const [email, setEmail] = useState(typeof params.email === "string" ? params.email : "");
  const [code, setCode] = useState(typeof params.code === "string" ? params.code : "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await post("/auth/reset-password", { email: email.trim(), code: code.trim(), new_password: password });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="reset-password-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>WELLSTRIDE</Text>
        <Text style={styles.heroTitle}>{t.resetTitle}</Text>
        <Text style={styles.heroSub}>{done ? t.resetDone : t.resetSub}</Text>
        <View style={styles.authCard}>
          {done ? (
            <Button testID="reset-back-button" label={t.backToSignIn} onPress={() => {
              // Clear the whole stack first, so the sign-in screen is not left under a second copy of itself.
              router.dismissAll();
              router.replace("/");
            }} />
          ) : (
            <>
              <Field label={t.email} value={email} onChangeText={setEmail} />
              <Field label={t.resetCode} value={code} onChangeText={setCode} />
              <Field label={t.newPassword} value={password} onChangeText={setPassword} secureTextEntry />
              {error ? <Text style={styles.errorText} testID="reset-error">{error}</Text> : null}
              <Button testID="reset-submit-button" label={busy ? "..." : t.resetButton} onPress={submit} disabled={busy || !email || code.trim().length < 4 || password.length < 8} />
            </>
          )}
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
