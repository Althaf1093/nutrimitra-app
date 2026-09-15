import { QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { LogBox } from "react-native";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { AuthProvider } from "@/src/context/auth";
import { queryClient } from "@/src/query-client";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

export default function RootLayout() {
  // One app level ErrorBoundary; a render crash shows a reload screen
  // instead of a blank app.
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <KeyboardProvider>
          <AuthProvider>
            <StatusBar style="dark" />
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="eat-now" options={{ presentation: "modal" }} />
              <Stack.Screen name="log-food" options={{ presentation: "modal" }} />
              <Stack.Screen name="settings" options={{ presentation: "modal" }} />
            </Stack>
          </AuthProvider>
        </KeyboardProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
