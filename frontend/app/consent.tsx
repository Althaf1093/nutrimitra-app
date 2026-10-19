import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { Button } from "@/src/components/ui";
import { ConsentCheckbox, LegalLinks } from "@/src/components/legal-links";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

// Shown once to accounts that have not agreed to the current Terms and Privacy Policy (made before consent existed,
// or before the policies last changed).
export default function ConsentScreen() {
  const styles = useStyles();
  const router = useRouter();
  const { status, t, acceptConsent, signOut } = useAuth();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (status === "anon") return <Redirect href="/welcome" />;
  if (status === "ready") return <Redirect href="/(tabs)" />;
  if (status === "onboarding") return <Redirect href="/onboarding" />;

  const agree = async () => {
    setBusy(true);
    setError("");
    try {
      await acceptConsent();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.pleaseTryAgain);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root} testID="consent-screen">
      <KeyboardAwareScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>WELLSTRIDE</Text>
        <Text style={styles.heroTitle}>{t.consentTitle}</Text>
        <Text style={styles.heroSub}>{t.consentSub}</Text>
        <View style={styles.authCard}>
          <ConsentCheckbox checked={accepted} onChange={setAccepted} />
          <LegalLinks />
          {error ? <Text style={styles.errorText} testID="consent-error">{error}</Text> : null}
          <Button testID="consent-continue-button" label={busy ? "..." : t.consentContinue} onPress={agree} disabled={busy || !accepted} />
          <Button
            testID="consent-sign-out-button"
            label={t.signOut}
            secondary
            onPress={async () => {
              await signOut();
              router.replace("/");
            }}
          />
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}
