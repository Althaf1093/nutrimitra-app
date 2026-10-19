import { Linking, Text, View } from "react-native";

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
