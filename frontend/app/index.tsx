import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";

import { useAuth } from "@/src/context/auth";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";

export default function Index() {
  const { status } = useAuth();
  const styles = useStyles();
  const { colors } = useTheme();

  if (status === "loading") {
    return (
      <View style={styles.center} testID="auth-loading">
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }
  if (status === "anon") return <Redirect href="/welcome" />;
  if (status === "onboarding") return <Redirect href="/onboarding" />;
  return <Redirect href="/(tabs)" />;
}
