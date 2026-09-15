import { Platform, StyleSheet } from "react-native";

import { makeStyles } from "@/src/theme";

const serif = Platform.select({ ios: "Georgia", default: "serif" });

// Responsive rules baked in everywhere:
// - `flex` carries minWidth: 0 so text can shrink inside rows instead of
//   collapsing to one character per line.
// - Every display/heading style declares an explicit lineHeight so tall
//   scripts (Telugu) never clip on Android/iOS.
// - Chips cap at maxWidth: "100%" so long translations never overflow.
// Web previews shape Telugu conjuncts poorly with system fallbacks, so the
// bundled Noto Sans Telugu (Latin + Telugu) leads the web font stack. Native
// devices render Telugu natively — this is a no-op there.
function withTeluguFallback<T>(sheet: T): T {
  if (Platform.OS !== "web") return sheet;
  const patched: Record<string, Record<string, unknown>> = {};
  for (const [key, style] of Object.entries(sheet as Record<string, Record<string, unknown>>)) {
    if (style && ("fontSize" in style || "lineHeight" in style || "fontWeight" in style)) {
      patched[key] = { ...style, fontFamily: style.fontFamily ? `NotoSansTelugu, ${style.fontFamily}` : "NotoSansTelugu, System" };
    } else {
      patched[key] = style;
    }
  }
  return patched as T;
}

export const useStyles = makeStyles((colors) =>
  withTeluguFallback(
    StyleSheet.create({
    root: { flex: 1, backgroundColor: colors.surface },
    flex: { flex: 1, minWidth: 0 },
    center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: colors.surface },
    pressed: { opacity: 0.78, transform: [{ scale: 0.985 }] },
    disabled: { opacity: 0.45 },

    brandMark: { width: 54, height: 54, borderRadius: 18, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", marginBottom: 20 },
    brandIcon: { color: colors.onBrandPrimary },
    authContent: { flexGrow: 1, padding: 24, paddingTop: 58, paddingBottom: 32, maxWidth: 620, width: "100%", alignSelf: "center" },
    languagePill: { position: "absolute", right: 24, top: 56, minHeight: 44, paddingHorizontal: 14, borderRadius: 22, backgroundColor: colors.surfaceSecondary, justifyContent: "center" },
    languageText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "600" },
    eyebrow: { color: colors.brandSecondary, fontSize: 11, letterSpacing: 1.4, fontWeight: "700", lineHeight: 16 },
    heroTitle: { color: colors.onSurface, fontSize: 36, lineHeight: 44, fontFamily: serif, marginTop: 10, maxWidth: 390 },
    heroSub: { color: colors.onSurfaceSecondary, fontSize: 16, lineHeight: 24, marginTop: 12, maxWidth: 440 },
    authCard: { backgroundColor: colors.surfaceSecondary, borderRadius: 24, padding: 18, marginTop: 32, borderWidth: 1, borderColor: colors.border },
    authTabs: { flexDirection: "row", backgroundColor: colors.surfaceTertiary, borderRadius: 12, padding: 4, marginBottom: 18 },
    authTab: { flex: 1, minWidth: 0, minHeight: 44, alignItems: "center", justifyContent: "center", borderRadius: 9, paddingHorizontal: 6 },
    authTabActive: { backgroundColor: colors.surface, shadowColor: colors.surfaceInverse, shadowOpacity: 0.08, shadowRadius: 8, shadowOffset: { width: 0, height: 2 } },
    authTabText: { color: colors.muted, fontSize: 14, fontWeight: "600", textAlign: "center" },
    authTabActiveText: { color: colors.onSurface, fontSize: 14, fontWeight: "700", textAlign: "center" },
    authHint: { color: colors.muted, fontSize: 13, lineHeight: 19, textAlign: "center", marginTop: 18 },
    safeNote: { color: colors.muted, fontSize: 12, lineHeight: 17, textAlign: "center", marginTop: 22 },

    field: { marginBottom: 14 },
    fieldLabel: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", lineHeight: 18, marginBottom: 8 },
    input: { minHeight: 50, borderRadius: 12, borderWidth: 1, borderColor: colors.borderStrong, backgroundColor: colors.surface, paddingHorizontal: 14, color: colors.onSurface, fontSize: 15 },
    errorText: { color: colors.error, fontSize: 13, lineHeight: 18, marginBottom: 4 },

    button: { minHeight: 50, borderRadius: 14, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", paddingHorizontal: 18, marginTop: 8 },
    buttonText: { color: colors.onBrandPrimary, fontSize: 15, fontWeight: "700", lineHeight: 20, textAlign: "center" },
    buttonSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderStrong },
    buttonSecondaryText: { color: colors.onSurface, fontSize: 15, fontWeight: "700", lineHeight: 20, textAlign: "center" },
    linkText: { color: colors.brandPrimary, fontWeight: "700" },

    onboardingContent: { padding: 24, paddingTop: 58, paddingBottom: 40, maxWidth: 620, width: "100%", alignSelf: "center" },
    stepTop: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", gap: 12 },
    stepCounter: { color: colors.onSurface, fontSize: 15, fontWeight: "700", lineHeight: 21, flexShrink: 1, textAlign: "right" },
    progressTrack: { height: 6, borderRadius: 3, backgroundColor: colors.surfaceTertiary, marginTop: 14, overflow: "hidden" },
    progressFill: { height: 6, backgroundColor: colors.brandPrimary, borderRadius: 3 },
    sectionTitle: { color: colors.onSurface, fontSize: 28, lineHeight: 36, fontFamily: serif, marginTop: 28 },
    sectionSub: { color: colors.onSurfaceSecondary, fontSize: 15, lineHeight: 22, marginTop: 6, marginBottom: 20 },
    formStack: { gap: 7 },
    row: { flexDirection: "row", gap: 12 },
    half: { flex: 1, minWidth: 0 },
    chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 14 },
    chip: { flexShrink: 0, maxWidth: "100%", minHeight: 44, paddingHorizontal: 14, borderRadius: 22, borderWidth: 1, borderColor: colors.borderStrong, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" },
    chipSelected: { backgroundColor: colors.brandTertiary, borderColor: colors.brandSecondary },
    chipText: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", lineHeight: 18, flexShrink: 1 },
    chipSelectedText: { color: colors.onBrandTertiary, fontSize: 13, fontWeight: "700", lineHeight: 18, flexShrink: 1 },
    stickyActions: { flexDirection: "row", gap: 10, marginTop: 24 },

    appHeader: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
    headerTitle: { color: colors.onSurface, fontSize: 26, lineHeight: 34, fontFamily: serif, marginTop: 5 },
    iconButton: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, flexShrink: 0 },
    screenContent: { alignSelf: "center", width: "100%", maxWidth: 620, padding: 20, paddingBottom: 40 },

    readinessCard: { borderRadius: 24, padding: 22, backgroundColor: colors.brandPrimary, flexDirection: "row", justifyContent: "space-between", alignItems: "center", minHeight: 158, gap: 12 },
    cardEyebrow: { color: colors.brandSecondary, fontSize: 11, letterSpacing: 1.2, fontWeight: "700", lineHeight: 16 },
    cardEyebrowOnDark: { color: colors.brandTertiary, fontSize: 11, letterSpacing: 1.2, fontWeight: "700", lineHeight: 16 },
    readinessValue: { color: colors.onBrandPrimary, fontSize: 46, lineHeight: 54, fontWeight: "700", marginTop: 6 },
    readinessSlash: { color: colors.brandTertiary, fontSize: 16, fontWeight: "500" },
    cardCaption: { color: colors.brandTertiary, fontSize: 13, lineHeight: 18, marginTop: 4 },
    readinessRing: { width: 92, height: 92, borderRadius: 46, borderWidth: 8, borderColor: colors.brandTertiary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    ringText: { color: colors.onBrandPrimary, fontSize: 20, lineHeight: 24, fontWeight: "700" },
    ringCaption: { color: colors.brandTertiary, fontSize: 10, lineHeight: 13, marginTop: 3, textAlign: "center", paddingHorizontal: 6 },
    eatBanner: { backgroundColor: colors.brandTertiary, borderRadius: 20, padding: 16, marginTop: 14, flexDirection: "row", alignItems: "center", gap: 12 },
    bannerIcon: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    bannerTitle: { color: colors.onSurface, fontSize: 16, fontWeight: "700", lineHeight: 22 },
    bannerSub: { color: colors.onSurfaceSecondary, fontSize: 12, lineHeight: 17, marginTop: 3 },
    sectionHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 28, marginBottom: 12 },
    sectionTitleSmall: { color: colors.onSurface, fontSize: 20, lineHeight: 27, fontWeight: "700" },
    mutedText: { color: colors.muted, fontSize: 13, lineHeight: 19 },
    mealCard: { backgroundColor: colors.surfaceSecondary, borderRadius: 18, padding: 14, flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 10, borderWidth: 1, borderColor: colors.border },
    mealDot: { width: 42, height: 42, borderRadius: 14, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    mealType: { color: colors.brandSecondary, fontSize: 10, letterSpacing: 1, fontWeight: "700", lineHeight: 14 },
    mealName: { color: colors.onSurface, fontSize: 15, fontWeight: "700", lineHeight: 20, marginTop: 3 },
    mealMeta: { color: colors.muted, fontSize: 12, lineHeight: 17, marginTop: 4 },
    logButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.borderStrong, flexShrink: 0 },
    logButtonText: { color: colors.brandPrimary, fontSize: 25, lineHeight: 27, fontWeight: "400" },
    reasonCard: { backgroundColor: colors.surfaceSecondary, borderLeftWidth: 3, borderLeftColor: colors.brandSecondary, padding: 17, borderRadius: 14, marginTop: 12 },
    reasonText: { color: colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21, marginTop: 7 },
    dayRow: { gap: 8, paddingVertical: 6, paddingHorizontal: 2 },
    planIntro: { marginVertical: 14, padding: 16, backgroundColor: colors.surfaceTertiary, borderRadius: 16 },
    planDay: { color: colors.onSurface, fontSize: 20, lineHeight: 27, fontWeight: "700" },

    syncCard: { flexDirection: "row", alignItems: "center", gap: 12, padding: 15, borderRadius: 18, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, marginBottom: 26 },
    syncIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    syncIconTint: { color: colors.brandPrimary },
    statusPill: { color: colors.success, fontSize: 11, fontWeight: "700", lineHeight: 15, backgroundColor: colors.surface, paddingHorizontal: 8, paddingVertical: 6, borderRadius: 10, flexShrink: 0 },
    activityHero: { flexDirection: "row", alignItems: "center", gap: 18, padding: 20, borderRadius: 22, backgroundColor: colors.surfaceTertiary, marginVertical: 16 },
    bigRing: { width: 106, height: 106, borderRadius: 53, borderWidth: 9, borderColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    bigRingValue: { color: colors.brandPrimary, fontSize: 22, lineHeight: 27, fontWeight: "700" },
    bigRingCaption: { color: colors.onSurfaceSecondary, fontSize: 11, lineHeight: 15, marginTop: 2 },
    successText: { color: colors.success, textAlign: "center", fontSize: 14, fontWeight: "700", lineHeight: 19, marginTop: 14 },

    chartCard: { padding: 18, borderRadius: 20, backgroundColor: colors.surfaceSecondary, marginTop: 8 },
    chart: { height: 154, flexDirection: "row", alignItems: "flex-end", gap: 12, borderBottomWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 8, paddingTop: 18, marginVertical: 14 },
    chartCol: { flex: 1, minWidth: 0, alignItems: "center", justifyContent: "flex-end", height: 130, gap: 6 },
    chartBar: { width: "72%", maxWidth: 34, borderRadius: 8, backgroundColor: colors.brandPrimary, minHeight: 12 },
    chartLabel: { color: colors.muted, fontSize: 10, lineHeight: 13 },
    inlineForm: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 14 },
    inlineInput: { flex: 1, minWidth: 0, minHeight: 50, borderRadius: 14, borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 14, color: colors.onSurface, backgroundColor: colors.surface },
    placeholder: { color: colors.muted },
    disclaimer: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 22 },

    chatContent: { flexGrow: 1, padding: 20, paddingBottom: 18, maxWidth: 620, width: "100%", alignSelf: "center" },
    coachBubble: { alignSelf: "flex-start", maxWidth: "88%", backgroundColor: colors.surfaceSecondary, borderRadius: 18, borderTopLeftRadius: 5, padding: 14, marginBottom: 12 },
    userBubble: { alignSelf: "flex-end", maxWidth: "88%", backgroundColor: colors.brandPrimary, borderRadius: 18, borderTopRightRadius: 5, padding: 14, marginBottom: 12 },
    coachBubbleText: { color: colors.onSurface, fontSize: 15, lineHeight: 22 },
    userBubbleText: { color: colors.onBrandPrimary, fontSize: 15, lineHeight: 22 },
    quickRow: { gap: 8, marginTop: 10 },
    chatComposer: { flexDirection: "row", gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: colors.divider, backgroundColor: colors.surface },
    chatInput: { flex: 1, minWidth: 0, minHeight: 48, borderRadius: 24, borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 16, color: colors.onSurface, backgroundColor: colors.surfaceSecondary },
    sendButton: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center", backgroundColor: colors.brandPrimary, flexShrink: 0 },
    sendIcon: { color: colors.onBrandPrimary },

    recipeCard: { alignSelf: "flex-start", width: "100%", maxWidth: "100%", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 16, padding: 16, marginTop: -4, marginBottom: 12 },
    recipeTitle: { color: colors.onSurface, fontSize: 17, lineHeight: 23, fontWeight: "700", marginTop: 6 },
    recipeLabel: { color: colors.brandSecondary, fontSize: 11, letterSpacing: 1, fontWeight: "700", lineHeight: 16, marginTop: 14, marginBottom: 4 },
    recipeItem: { color: colors.onSurfaceSecondary, fontSize: 13, lineHeight: 20 },

    toast: { position: "absolute", left: 20, right: 20, bottom: 96, backgroundColor: colors.surfaceInverse, padding: 14, borderRadius: 14 },
    toastText: { color: colors.onSurfaceInverse, textAlign: "center", fontSize: 13, fontWeight: "600", lineHeight: 18 },

    macroRow: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginVertical: 18 },
    macro: { color: colors.onSurfaceSecondary, backgroundColor: colors.surfaceTertiary, paddingHorizontal: 10, paddingVertical: 8, borderRadius: 10, fontSize: 12, fontWeight: "600", lineHeight: 16 },
    modalTitle: { color: colors.onSurface, fontSize: 26, lineHeight: 34, fontFamily: serif, marginTop: 8 },
    modalMeal: { color: colors.brandPrimary, fontSize: 21, lineHeight: 28, fontWeight: "700", marginTop: 16 },
    modalSub: { color: colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21, marginTop: 7, marginBottom: 12 },
    settingRow: { flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: colors.divider },
    switchTrack: { width: 48, height: 28, padding: 3, borderRadius: 16, backgroundColor: colors.surfaceTertiary, justifyContent: "center", flexShrink: 0 },
    switchOn: { backgroundColor: colors.brandPrimary },
    switchKnob: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.surface, transform: [{ translateX: 0 }] },
    switchKnobOn: { transform: [{ translateX: 20 }] },

    photoPreview: { width: "100%", height: 230, borderRadius: 18, overflow: "hidden", backgroundColor: colors.surfaceTertiary, marginTop: 16 },
    stickyCta: { padding: 16, borderTopWidth: 1, borderTopColor: colors.divider, backgroundColor: colors.surface },
    })
  )
);
