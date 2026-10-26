// Design tokens for Wellstride: colours (light and dark), spacing, radii, type, shadows and motion. This is the only place
// that holds raw colours or sizes; screens and components read them from here.
//
// How colour names work: a plain key is a background, and its `on` partner is the text or icon colour that sits on top of it.
//   <View style={{ backgroundColor: colors.brandPrimary }}>
//     <Text style={{ color: colors.onBrandPrimary }}>Continue</Text>
//   </View>
//
// Styling a screen or component: build the sheet with makeStyles so colours and layout live together and follow the scheme:
//   const useStyles = makeStyles((colors, fonts) => ({
//     card: { backgroundColor: colors.card, padding: space.lg, borderRadius: radius.lg, boxShadow: colors.shadowCard },
//   }));
// For colour props that are not styles (icon colour, placeholderTextColor, ActivityIndicator) read useTheme().colors.
// Never call StyleSheet.create with colour values at module level; it cannot follow the scheme.
//
// Dark mode follows the device unless the person picks Light or Dark in Settings (setThemePreference).

import AsyncStorage from "@react-native-async-storage/async-storage";
import { useCallback, useMemo, useSyncExternalStore } from "react";
import { Platform, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";
export type ThemePreference = "system" | "light" | "dark";

const light = {
  // Surfaces, from the screen down to small fills. Each `on` key is the text and icon colour for that background.
  surface: "#FBF8F2",
  onSurface: "#1F2A25",
  surfaceSecondary: "#FFFFFF",
  onSurfaceSecondary: "#3B4640",
  surfaceTertiary: "#F1ECE1",
  onSurfaceTertiary: "#4F5A53",
  surfaceInverse: "#1F2A25",
  onSurfaceInverse: "#FBF8F2",
  muted: "#5E6862",
  card: "#FFFFFF",
  onCard: "#1F2A25",

  // Brand: the sage green anchor and the fills built from it.
  brand: "#4A6B5D",
  onBrand: "#FFFFFF",
  brandPrimary: "#3F6254",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#8A5A1E",
  onBrandSecondary: "#FFFFFF",
  brandTertiary: "#E4EEE8",
  onBrandTertiary: "#24382F",
  brandSoft: "#E4EEE8",
  brandFaint: "#F1F6F3",

  // Accent: warm saffron for calories and highlights.
  accent: "#C26E1B",
  onAccent: "#FFFFFF",
  accentSoft: "#FBEBD6",
  onAccentSoft: "#7A430B",

  // Hero cards (the calorie summary): a deep green block with light text and a saffron progress colour.
  hero: "#3F6254",
  onHero: "#FFFFFF",
  heroTrack: "rgba(255,255,255,0.18)",
  heroAccent: "#F4B563",

  // Macros: distinct colours that keep their contrast on the card, and their soft tints.
  macroProtein: "#2F7F6F",
  macroCarbs: "#B9831A",
  macroFat: "#D0553F",
  macroFibre: "#6F5DB0",
  macroProteinSoft: "#DDF0EA",
  macroCarbsSoft: "#F7EBCB",
  macroFatSoft: "#F6E3DF",
  macroFibreSoft: "#E9E5F4",
  water: "#2B7BB0",
  waterSoft: "#E3EEF6",

  // Status: semantic only, never decorative. The plain key is also safe as text on `surface`.
  success: "#4B7A45",
  onSuccess: "#FFFFFF",
  warning: "#A06A1A",
  onWarning: "#FFFFFF",
  error: "#A33F39",
  onError: "#FFFFFF",
  info: "#2B6F94",
  onInfo: "#FFFFFF",

  // Lines and depth
  border: "#ECE6DA",
  borderStrong: "#CFC5B3",
  divider: "#F0EBE0",
  scrim: "rgba(20,28,24,0.45)",
  shadowCard: "0 1px 2px rgba(31,42,37,0.05), 0 8px 24px rgba(31,42,37,0.06)",
  shadowRaised: "0 2px 4px rgba(31,42,37,0.08), 0 16px 40px rgba(31,42,37,0.14)",
};

export type ThemeColors = typeof light;

const dark: ThemeColors = {
  surface: "#111815",
  onSurface: "#ECF1EE",
  surfaceSecondary: "#1A241F",
  onSurfaceSecondary: "#CAD5CF",
  surfaceTertiary: "#222E28",
  onSurfaceTertiary: "#B5C2BB",
  surfaceInverse: "#ECF1EE",
  onSurfaceInverse: "#111815",
  muted: "#9BAAA2",
  card: "#1A241F",
  onCard: "#ECF1EE",

  brand: "#7FB59F",
  onBrand: "#0E1A14",
  brandPrimary: "#86BDA7",
  onBrandPrimary: "#0E1A14",
  brandSecondary: "#E2B070",
  onBrandSecondary: "#1F1406",
  brandTertiary: "#2A3D34",
  onBrandTertiary: "#D6EBE0",
  brandSoft: "#2A3D34",
  brandFaint: "#1E2B25",

  accent: "#F0A24A",
  onAccent: "#2A1705",
  accentSoft: "#3A2A14",
  onAccentSoft: "#F6C98B",

  hero: "#24382F",
  onHero: "#F4F8F5",
  heroTrack: "rgba(255,255,255,0.16)",
  heroAccent: "#F4B563",

  macroProtein: "#6CCDB6",
  macroCarbs: "#E7BC5A",
  macroFat: "#F08A75",
  macroFibre: "#B3A6E8",
  macroProteinSoft: "#1C3A33",
  macroCarbsSoft: "#3A3018",
  macroFatSoft: "#3E2621",
  macroFibreSoft: "#2B2742",
  water: "#6AB4E3",
  waterSoft: "#1B3040",

  success: "#8FC987",
  onSuccess: "#0E1A14",
  warning: "#E7B068",
  onWarning: "#1F1406",
  error: "#F09089",
  onError: "#2A0E0C",
  info: "#7FC0E4",
  onInfo: "#0B1C26",

  border: "#2A3731",
  borderStrong: "#42524A",
  divider: "#222D27",
  scrim: "rgba(0,0,0,0.6)",
  shadowCard: "0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.25)",
  shadowRaised: "0 2px 4px rgba(0,0,0,0.4), 0 16px 40px rgba(0,0,0,0.5)",
};

export const themes: { light: ThemeColors; dark: ThemeColors } = { light, dark };

// Spacing, corner radii, type scale and motion: one scale for the whole app.
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, huge: 32 } as const;
export const radius = { sm: 10, md: 14, lg: 22, xl: 28, pill: 999 } as const;
export const type = { caption: 12, small: 13, body: 15, bodyLg: 16, title: 19, h2: 22, h1: 28, display: 34 } as const;
export const motion = { fast: 120, base: 200, slow: 360 } as const;
export const layout = { tabletMin: 600, desktopMin: 1024, contentMax: 1120, sidebar: 264, phoneContent: 620 } as const;

// ---------------------------------------------------------------------------------------------------------------------
// Fonts: Plus Jakarta Sans for English, Noto Sans Telugu for Telugu. React Native picks a font file by family name, so each
// weight is its own family; withFonts() in styles.ts swaps `fontWeight` for the matching family.
// ---------------------------------------------------------------------------------------------------------------------
export type FontLanguage = "en" | "te";
export type FontSet = { 400: string; 500: string; 600: string; 700: string; 800: string };

export const fontFamilies: Record<FontLanguage, FontSet> = {
  en: { 400: "PlusJakartaSans_400Regular", 500: "PlusJakartaSans_500Medium", 600: "PlusJakartaSans_600SemiBold", 700: "PlusJakartaSans_700Bold", 800: "PlusJakartaSans_800ExtraBold" },
  // Telugu ships three weights; the in-between ones use the nearest (500 -> 400, 800 -> 700).
  te: { 400: "NotoSansTelugu_400Regular", 500: "NotoSansTelugu_400Regular", 600: "NotoSansTelugu_600SemiBold", 700: "NotoSansTelugu_700Bold", 800: "NotoSansTelugu_700Bold" },
};
export type Fonts = FontSet & { language: FontLanguage };

// ---------------------------------------------------------------------------------------------------------------------
// Preferences kept outside React so every hook sees them: the light/dark choice and the language the fonts follow.
// ---------------------------------------------------------------------------------------------------------------------
const PREFERENCE_KEY = "nutrimitra.theme";
type Snapshot = { preference: ThemePreference; language: FontLanguage };
let snapshot: Snapshot = { preference: "system", language: "en" };
const listeners = new Set<() => void>();

function publish(next: Partial<Snapshot>) {
  snapshot = { ...snapshot, ...next };
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const getSnapshot = () => snapshot;

/** Read the saved light/dark choice once at start-up. Safe to call when storage is unavailable. */
export async function loadThemePreference() {
  try {
    const saved = await AsyncStorage.getItem(PREFERENCE_KEY);
    if (saved === "light" || saved === "dark" || saved === "system") publish({ preference: saved });
  } catch {
    // Storage can be blocked (private windows); the device setting applies.
  }
}

export function setThemePreference(preference: ThemePreference) {
  publish({ preference });
  AsyncStorage.setItem(PREFERENCE_KEY, preference).catch(() => undefined);
}

/** The fonts follow the interface language; the auth context calls this when it changes. */
export function setFontLanguage(language: FontLanguage) {
  if (snapshot.language !== language) publish({ language });
}

export function useThemePreference(): { preference: ThemePreference; setPreference: (preference: ThemePreference) => void } {
  const { preference } = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const setPreference = useCallback((next: ThemePreference) => setThemePreference(next), []);
  return { preference, setPreference };
}

// The device's light/dark setting. react-native-web reads it once, so on the web we listen for changes ourselves.
const webQuery = () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null);
function subscribeWeb(listener: () => void) {
  const query = webQuery();
  query?.addEventListener("change", listener);
  return () => query?.removeEventListener("change", listener);
}
const webDark = () => webQuery()?.matches ?? false;

function useSystemScheme(): "light" | "dark" {
  const native = useColorScheme();
  // eslint-disable-next-line react-hooks/rules-of-hooks -- Platform.OS never changes while the app runs
  const web = Platform.OS === "web" ? useSyncExternalStore(subscribeWeb, webDark, () => false) : false;
  return Platform.OS === "web" ? (web ? "dark" : "light") : native === "dark" ? "dark" : "light";
}

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors; fonts: Fonts } {
  const system = useSystemScheme();
  const { preference, language } = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const scheme: ColorScheme = preference === "system" ? (system === "dark" ? "dark" : "light") : preference;
  const fonts = useMemo<Fonts>(() => ({ ...fontFamilies[language], language }), [language]);
  return { scheme, colors: themes[scheme], fonts };
}

/** Letter spacing pulls apart (or crushes) the joined letters of Telugu, so Telugu text never gets any. */
export function withoutTeluguSpacing<T>(sheet: T, language: FontLanguage): T {
  if (language !== "te") return sheet;
  const out: Record<string, unknown> = {};
  for (const [key, style] of Object.entries(sheet as Record<string, unknown>)) {
    if (style && typeof style === "object" && "letterSpacing" in style) {
      const { letterSpacing: _dropped, ...rest } = style as Record<string, unknown>;
      out[key] = rest;
    } else out[key] = style;
  }
  return out as T;
}

// Themed StyleSheet: returns a hook that builds the sheet from the active scheme's colours and fonts and memoizes it.
export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors, fonts: Fonts) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors, fonts } = useTheme();
    return useMemo(() => StyleSheet.create(withoutTeluguSpacing(factory(colors, fonts), fonts.language)), [colors, fonts]);
  };
}
