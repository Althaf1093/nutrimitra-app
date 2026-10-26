import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AccessibilityInfo, Animated, PanResponder, Platform, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";

export type ToastType = "success" | "info" | "error";
export type ToastOptions = {
  type?: ToastType;
  /** Label and handler for a button inside the toast, e.g. Undo. */
  actionLabel?: string;
  onAction?: () => void;
  /** Milliseconds before it goes away. Defaults: 2500, or 4000 for errors and toasts with an action. */
  duration?: number;
  /** Extra space above the usual spot, for a screen with its own bar at the bottom (the Coach chat box). */
  raise?: number;
};
type ToastApi = { show: (message: string, options?: ToastOptions) => void; hide: () => void };
type ToastState = ToastOptions & { id: number; message: string };

const SHORT_MS = 2500;
const LONG_MS = 4000;
const GLYPH: Record<ToastType, string> = { success: "✓", info: "i", error: "!" };

const noop: ToastApi = { show: () => undefined, hide: () => undefined };
const ToastContext = createContext<ToastApi>(noop);

/** useToast().show("Meal logged", { actionLabel: "Undo", onAction }). One toast at a time: a new one replaces the old. */
export function useToast(): ToastApi {
  return useContext(ToastContext);
}

export function toastDuration(options: ToastOptions): number {
  return options.duration ?? (options.type === "error" || options.actionLabel ? LONG_MS : SHORT_MS);
}

/** `bottom` is the gap above the screen edge; the app's root provider clears the tab bar, a modal can sit lower. */
export function ToastProvider({ children, bottom }: { children: ReactNode; bottom?: number }) {
  const insets = useSafeAreaInsets();
  const [toast, setToast] = useState<ToastState | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const counter = useRef(0);

  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  const hide = useCallback(() => {
    clearTimer();
    setToast(null);
  }, []);

  const show = useCallback((message: string, options: ToastOptions = {}) => {
    clearTimer();
    counter.current += 1;
    const next: ToastState = { ...options, type: options.type ?? "success", id: counter.current, message };
    setToast(next);
    timer.current = setTimeout(() => setToast((current) => (current?.id === next.id ? null : current)), toastDuration(next));
    if (Platform.OS !== "web") AccessibilityInfo.announceForAccessibility(message);
  }, []);

  useEffect(() => clearTimer, []);

  const api = useMemo(() => ({ show, hide }), [show, hide]);
  // Above the tab bar: 64 px on the web, about 50 px plus the home indicator on a phone.
  const offset = bottom ?? (Platform.OS === "web" ? 76 : insets.bottom + 68);

  return (
    <ToastContext.Provider value={api}>
      <View style={{ flex: 1 }}>
        {children}
        {toast ? <ToastView key={toast.id} toast={toast} bottom={offset + (toast.raise ?? 0)} onClose={hide} /> : null}
      </View>
    </ToastContext.Provider>
  );
}

function ToastView({ toast, bottom, onClose }: { toast: ToastState; bottom: number; onClose: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const type = toast.type ?? "success";
  const [appear] = useState(() => new Animated.Value(0));
  const [drag] = useState(() => new Animated.ValueXY({ x: 0, y: 0 }));
  const native = Platform.OS !== "web";

  useEffect(() => {
    Animated.timing(appear, { toValue: 1, duration: 180, useNativeDriver: native }).start();
  }, [appear, native]);

  // Swipe sideways or down to dismiss; a short drag springs back.
  const [pan] = useState(() =>
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 8 || g.dy > 8,
      onPanResponderMove: Animated.event([null, { dx: drag.x, dy: drag.y }], { useNativeDriver: false }),
      onPanResponderRelease: (_, g) => {
        if (Math.abs(g.dx) > 70 || g.dy > 30) onClose();
        else Animated.spring(drag, { toValue: { x: 0, y: 0 }, useNativeDriver: false }).start();
      },
    }),
  );

  const fill = type === "error" ? colors.error : type === "info" ? colors.info : colors.success;
  const onFill = type === "error" ? colors.onError : type === "info" ? colors.onInfo : colors.onSuccess;
  const slide = appear.interpolate({ inputRange: [0, 1], outputRange: [14, 0] });

  return (
    <View pointerEvents="box-none" style={[styles.toastHost, { bottom }]}>
      <Animated.View
        testID="toast"
        role={type === "error" ? "alert" : "status"}
        accessibilityLiveRegion={type === "error" ? "assertive" : "polite"}
        style={{ opacity: appear, maxWidth: "100%", transform: [{ translateY: slide }, { translateX: drag.x }, { translateY: drag.y }] }}
        {...pan.panHandlers}
      >
        {/* A View, not a button: the dismiss area and the action are siblings, because a button cannot hold a button. */}
        <View style={styles.toast}>
          <Pressable accessibilityRole="button" accessibilityLabel={toast.message} onPress={onClose} style={{ flex: 1, minWidth: 0, flexDirection: "row", alignItems: "center", gap: 12 }}>
            <View style={[styles.toastIcon, { backgroundColor: fill }]} testID={`toast-icon-${type}`}>
              <Text style={[styles.toastIconText, { color: onFill }]}>{GLYPH[type]}</Text>
            </View>
            <Text style={[styles.toastText, { flex: 1 }]} testID="toast-message">
              {toast.message}
            </Text>
          </Pressable>
          {toast.actionLabel && toast.onAction ? (
            <Pressable
              testID="toast-action"
              accessibilityRole="button"
              accessibilityLabel={toast.actionLabel}
              hitSlop={8}
              onPress={() => {
                toast.onAction?.();
                onClose();
              }}
              style={styles.toastAction}
            >
              <Text style={styles.toastActionText}>{toast.actionLabel}</Text>
            </Pressable>
          ) : null}
        </View>
      </Animated.View>
    </View>
  );
}
