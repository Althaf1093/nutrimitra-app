import { useRouter } from "expo-router";
import type { ReactNode } from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useBreakpoint } from "@/src/lib/use-breakpoint";
import { makeStyles, radius } from "@/src/theme";

const useShell = makeStyles((colors) => ({
  root: { flex: 1, backgroundColor: colors.surface },
  host: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  scrim: { position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: colors.scrim },
  dialog: { width: "100%", maxWidth: 760, height: "92%", maxHeight: 900, backgroundColor: colors.surface, borderRadius: radius.xl, borderWidth: 1, borderColor: colors.border, overflow: "hidden", boxShadow: colors.shadowRaised },
}));

/** The frame of a modal screen: full screen on a phone or tablet, a centred dialog over a dimmed page on a wide screen. */
export function ModalShell({ children, testID }: { children: ReactNode; testID: string }) {
  const styles = useShell();
  const { isDesktop } = useBreakpoint();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  if (!isDesktop) {
    return (
      <View style={[styles.root, { paddingTop: insets.top }]} testID={testID}>
        {children}
      </View>
    );
  }
  return (
    <View style={styles.host}>
      <Pressable testID={`${testID}-scrim`} accessible={false} focusable={false} style={styles.scrim} onPress={() => router.back()} />
      <View testID={testID} style={styles.dialog}>
        {children}
      </View>
    </View>
  );
}
