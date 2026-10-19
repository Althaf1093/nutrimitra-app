import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { ToastProvider } from "@/src/components/toast";
import { AuthProvider } from "@/src/context/auth";

export default function RootLayout() {
  // Bundled Telugu font for web previews (native devices render Telugu with
  // system fonts). Non-blocking: the app renders while the font loads.
  useFonts({ NotoSansTelugu: require("../assets/fonts/NotoSansTelugu.ttf") });
  // One app level ErrorBoundary; a render crash shows a reload screen
  // instead of a blank app.
  return (
    <ErrorBoundary>
      <KeyboardProvider>
        <AuthProvider>
          <StatusBar style="dark" />
          <ToastProvider>
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="eat-now" options={{ presentation: "modal" }} />
              <Stack.Screen name="log-food" options={{ presentation: "modal" }} />
              <Stack.Screen name="settings" options={{ presentation: "modal" }} />
            </Stack>
          </ToastProvider>
        </AuthProvider>
      </KeyboardProvider>
    </ErrorBoundary>
  );
}
