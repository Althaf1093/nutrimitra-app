import { Linking, Pressable, Text, View } from "react-native";

import { backendUrl } from "@/src/api";
import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";

/** Opens one of the server's public pages ("privacy", "terms") in the browser. */
export const openLegalPage = (page: "privacy" | "terms") => Linking.openURL(`${backendUrl}/${page}`);

export function LegalLinks() {
  const styles = useStyles();
  const { t } = useAuth();
  return (
    <View style={styles.row}>
      <Text testID="legal-privacy-link" accessibilityRole="link" style={styles.linkText} onPress={() => openLegalPage("privacy")}>
        {t.privacyPolicy}
      </Text>
      <Text style={styles.mutedText}>{"  ·  "}</Text>
      <Text testID="legal-terms-link" accessibilityRole="link" style={styles.linkText} onPress={() => openLegalPage("terms")}>
        {t.termsOfUse}
      </Text>
    </View>
  );
}

/** The required "I am 18 or over and agree to the Terms and Privacy Policy" box. */
export function ConsentCheckbox({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  const styles = useStyles();
  const { t } = useAuth();
  return (
    <View style={styles.consentRow}>
      <Pressable testID="consent-checkbox" accessibilityRole="checkbox" accessibilityState={{ checked }} accessibilityLabel={`${t.consentBefore}${t.termsShort}${t.consentAnd}${t.privacyPolicy}${t.consentAfter}`} onPress={() => onChange(!checked)} style={[styles.consentBox, checked && styles.consentBoxOn]}>
        {checked ? <Text style={styles.consentTick}>✓</Text> : null}
      </Pressable>
      <Text style={[styles.mutedText, styles.flex]}>
        {t.consentBefore}
        <Text testID="consent-terms-link" accessibilityRole="link" style={styles.linkText} onPress={() => openLegalPage("terms")}>
          {t.termsShort}
        </Text>
        {t.consentAnd}
        <Text testID="consent-privacy-link" accessibilityRole="link" style={styles.linkText} onPress={() => openLegalPage("privacy")}>
          {t.privacyPolicy}
        </Text>
        {t.consentAfter}
      </Text>
    </View>
  );
}
