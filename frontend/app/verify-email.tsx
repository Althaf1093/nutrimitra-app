import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { post } from "@/src/api";
import { Button, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

// Enter the 6 digit code emailed at sign-up. Optional: the app works without it, but password reset needs a verified email.
export default function VerifyEmailScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { status, t, user, refreshUser } = useAuth();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [done, setDone] = useState(false);

  if (status === "anon") return <Redirect href="/welcome" />;

  const verify = async () => {
    setBusy(true);
    setError("");
    setNote("");
    try {
      await post("/auth/verify-email", { code: code.trim() });
      await refreshUser();
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  const resend = async () => {
    setBusy(true);
    setError("");
    setNote("");
    try {
      await post("/auth/resend-verification", {});
      setNote(t.verifySent);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="verify-email-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>WELLSTRIDE</Text>
        <Text style={styles.heroTitle}>{t.verifyTitle}</Text>
        <Text style={styles.heroSub}>{done ? t.verifyDone : `${t.verifySub} ${user?.email ?? ""}`}</Text>
        <View style={styles.authCard}>
          {done ? (
            <Button testID="verify-done-button" label={t.close} onPress={() => router.back()} />
          ) : (
            <>
              <Field label={t.verifyCode} value={code} onChangeText={setCode} keyboardType="numeric" />
              {error ? <Text style={styles.errorText} testID="verify-error">{error}</Text> : null}
              {note ? <Text style={styles.mutedText} testID="verify-note">{note}</Text> : null}
              <Button testID="verify-submit-button" label={busy ? "..." : t.verifyButton} onPress={verify} disabled={busy || code.trim().length < 4} />
              <Button testID="verify-resend-button" label={t.verifyResend} secondary onPress={resend} disabled={busy} />
              <Text style={styles.authHint}>
                <Text style={styles.linkText} onPress={() => router.back()} testID="verify-later-link">
                  {t.close}
                </Text>
              </Text>
            </>
          )}
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
