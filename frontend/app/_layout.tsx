import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { Platform } from "react-native";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { ToastProvider } from "@/src/components/toast";
import { AuthProvider } from "@/src/context/auth";
import { useBreakpoint } from "@/src/lib/use-breakpoint";
import { loadThemePreference, useTheme } from "@/src/theme";

SplashScreen.preventAutoHideAsync().catch(() => undefined);

// Plus Jakarta Sans (English) and Noto Sans Telugu (Telugu), both SIL Open Font License. One file per weight, because
// React Native picks a font by family name; see fontFamilies in src/theme.ts.
const FONT_FILES = {
  PlusJakartaSans_400Regular: require("@expo-google-fonts/plus-jakarta-sans/400Regular/PlusJakartaSans_400Regular.ttf"),
  PlusJakartaSans_500Medium: require("@expo-google-fonts/plus-jakarta-sans/500Medium/PlusJakartaSans_500Medium.ttf"),
  PlusJakartaSans_600SemiBold: require("@expo-google-fonts/plus-jakarta-sans/600SemiBold/PlusJakartaSans_600SemiBold.ttf"),
  PlusJakartaSans_700Bold: require("@expo-google-fonts/plus-jakarta-sans/700Bold/PlusJakartaSans_700Bold.ttf"),
  PlusJakartaSans_800ExtraBold: require("@expo-google-fonts/plus-jakarta-sans/800ExtraBold/PlusJakartaSans_800ExtraBold.ttf"),
  NotoSansTelugu_400Regular: require("@expo-google-fonts/noto-sans-telugu/400Regular/NotoSansTelugu_400Regular.ttf"),
  NotoSansTelugu_600SemiBold: require("@expo-google-fonts/noto-sans-telugu/600SemiBold/NotoSansTelugu_600SemiBold.ttf"),
  NotoSansTelugu_700Bold: require("@expo-google-fonts/noto-sans-telugu/700Bold/NotoSansTelugu_700Bold.ttf"),
};

export default function RootLayout() {
  const [fontsReady, fontError] = useFonts(FONT_FILES);
  const { scheme, colors } = useTheme();
  const { isDesktop } = useBreakpoint();

  useEffect(() => {
    loadThemePreference();
  }, []);

  useEffect(() => {
    if (fontsReady || fontError) SplashScreen.hideAsync().catch(() => undefined);
  }, [fontsReady, fontError]);

  // The page behind the app follows the theme, so there is no white flash or white edge in dark mode on the web.
  useEffect(() => {
    if (Platform.OS === "web" && typeof document !== "undefined") {
      document.documentElement.style.backgroundColor = colors.surface;
      document.body.style.backgroundColor = colors.surface;
      document.documentElement.style.colorScheme = scheme;
    }
  }, [colors.surface, scheme]);

  // Wait for the fonts (a few hundred milliseconds) so text never jumps from the fallback font to the real one.
  if (!fontsReady && !fontError) return null;

  // On a wide screen a modal is a dialog over a dimmed page (see ModalShell); on a phone it slides up as a full sheet.
  const modal = { presentation: isDesktop ? ("transparentModal" as const) : ("modal" as const), animation: isDesktop ? ("fade" as const) : undefined };
  // One app level ErrorBoundary; a render crash shows a reload screen instead of a blank app.
  return (
    <ErrorBoundary>
      <KeyboardProvider>
        <AuthProvider>
          <StatusBar style={scheme === "dark" ? "light" : "dark"} />
          <ToastProvider>
            <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.surface } }}>
              <Stack.Screen name="eat-now" options={modal} />
              <Stack.Screen name="log-food" options={modal} />
              <Stack.Screen name="settings" options={modal} />
              <Stack.Screen name="shopping-list" options={modal} />
              <Stack.Screen name="kitchen" options={modal} />
            </Stack>
          </ToastProvider>
        </AuthProvider>
      </KeyboardProvider>
    </ErrorBoundary>
  );
}
