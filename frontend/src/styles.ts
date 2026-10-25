import { Platform, StyleSheet } from "react-native";

import { fontFamilies, makeStyles, radius, type Fonts } from "@/src/theme";

// Responsive rules baked in everywhere:
// - `flex` carries minWidth: 0 so text can shrink inside rows instead of
//   collapsing to one character per line.
// - Every display/heading style declares an explicit lineHeight so tall
//   scripts (Telugu) never clip on Android/iOS.
// - Chips cap at maxWidth: "100%" so long translations never overflow.
// Fonts: React Native picks a font file by family name, so every text style gets the family for its weight (Plus Jakarta Sans
// for English, Noto Sans Telugu for Telugu) and loses `fontWeight`. On the web the other script follows as a fallback.
const WEIGHTS: Record<string, 400 | 500 | 600 | 700 | 800> = { normal: 400, bold: 700, "100": 400, "200": 400, "300": 400, "400": 400, "500": 500, "600": 600, "700": 700, "800": 800, "900": 800 };
function withFonts<T>(sheet: T, fonts: Fonts): T {
  const other = fontFamilies[fonts.language === "te" ? "en" : "te"];
  const patched: Record<string, Record<string, unknown>> = {};
  for (const [key, style] of Object.entries(sheet as Record<string, Record<string, unknown>>)) {
    if (style && ("fontSize" in style || "lineHeight" in style || "fontWeight" in style)) {
      const weight = WEIGHTS[String(style.fontWeight ?? "400")] ?? 400;
      const { fontWeight: _dropped, ...rest } = style;
      const family = fonts[weight];
      patched[key] = { ...rest, fontFamily: Platform.OS === "web" ? `${family}, ${other[weight]}, system-ui, sans-serif` : family };
    } else {
      patched[key] = style;
    }
  }
  return patched as T;
}

export const useStyles = makeStyles((colors, fonts) =>
  withFonts(
    StyleSheet.create({
    root: { flex: 1, backgroundColor: colors.surface },
    flex: { flex: 1, minWidth: 0 },
    center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: colors.surface },
    pressed: { opacity: 0.8, transform: [{ scale: 0.985 }] },
    disabled: { opacity: 0.45 },

    brandMark: { width: 54, height: 54, borderRadius: 18, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", marginBottom: 20 },
    brandIcon: { color: colors.onBrandPrimary },
    authContent: { flexGrow: 1, padding: 24, paddingTop: 58, paddingBottom: 32, maxWidth: 620, width: "100%", alignSelf: "center" },
    languagePill: { position: "absolute", right: 24, top: 56, minHeight: 44, paddingHorizontal: 16, borderRadius: 22, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, justifyContent: "center" },
    languageText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "600" },
    eyebrow: { color: colors.accent, fontSize: 11, letterSpacing: 1.4, fontWeight: "700", lineHeight: 16 },
    heroTitle: { color: colors.onSurface, fontSize: 36, lineHeight: 44, fontWeight: "800", letterSpacing: -0.6, marginTop: 10, maxWidth: 390 },
    heroSub: { color: colors.onSurfaceSecondary, fontSize: 16, lineHeight: 24, marginTop: 12, maxWidth: 440 },
    authCard: { backgroundColor: colors.card, borderRadius: radius.xl, padding: 20, marginTop: 32, borderWidth: 1, borderColor: colors.border, boxShadow: colors.shadowCard },
    authTabs: { flexDirection: "row", backgroundColor: colors.surfaceTertiary, borderRadius: 999, padding: 4, marginBottom: 18 },
    authTab: { flex: 1, minWidth: 0, minHeight: 44, alignItems: "center", justifyContent: "center", borderRadius: 999, paddingHorizontal: 6 },
    authTabActive: { backgroundColor: colors.card, boxShadow: colors.shadowCard },
    authTabText: { color: colors.muted, fontSize: 14, fontWeight: "600", textAlign: "center" },
    authTabActiveText: { color: colors.onSurface, fontSize: 14, fontWeight: "700", textAlign: "center" },
    authHint: { color: colors.muted, fontSize: 13, lineHeight: 19, textAlign: "center", marginTop: 18 },
    safeNote: { color: colors.muted, fontSize: 12, lineHeight: 17, textAlign: "center", marginTop: 22 },

    field: { marginBottom: 14 },
    fieldLabel: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", lineHeight: 18, marginBottom: 8 },
    input: { minHeight: 52, borderRadius: 16, borderWidth: 1, borderColor: colors.borderStrong, backgroundColor: colors.card, paddingHorizontal: 16, color: colors.onSurface, fontSize: 15 },
    errorText: { color: colors.error, fontSize: 13, lineHeight: 18, marginBottom: 4 },

    button: { minHeight: 52, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", paddingHorizontal: 22, marginTop: 8 },
    buttonText: { color: colors.onBrandPrimary, fontSize: 15, fontWeight: "700", lineHeight: 20, textAlign: "center" },
    buttonSecondary: { backgroundColor: "transparent", borderWidth: 1.5, borderColor: colors.brandPrimary },
    buttonSecondaryText: { color: colors.brandPrimary, fontSize: 15, fontWeight: "700", lineHeight: 20, textAlign: "center" },
    consentRow: { flexDirection: "row", alignItems: "flex-start", gap: 12, marginTop: 4, marginBottom: 4 },
    consentBox: { width: 26, height: 26, borderRadius: 8, borderWidth: 1.5, borderColor: colors.borderStrong, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", marginTop: 1 },
    consentBoxOn: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
    consentTick: { color: colors.onBrandPrimary, fontSize: 16, fontWeight: "700", lineHeight: 18 },
    linkText: { color: colors.brandPrimary, fontWeight: "700" },

    onboardingContent: { padding: 24, paddingTop: 58, paddingBottom: 40, maxWidth: 620, width: "100%", alignSelf: "center" },
    stepTop: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", gap: 12 },
    stepCounter: { color: colors.onSurface, fontSize: 15, fontWeight: "700", lineHeight: 21, flexShrink: 1, textAlign: "right" },
    progressTrack: { height: 6, borderRadius: 3, backgroundColor: colors.surfaceTertiary, marginTop: 14, overflow: "hidden" },
    progressFill: { height: 6, backgroundColor: colors.brandPrimary, borderRadius: 3 },
    sectionTitle: { color: colors.onSurface, fontSize: 28, lineHeight: 36, fontWeight: "800", letterSpacing: -0.4, marginTop: 28 },
    sectionSub: { color: colors.onSurfaceSecondary, fontSize: 15, lineHeight: 22, marginTop: 6, marginBottom: 20 },
    formStack: { gap: 7 },
    row: { flexDirection: "row", gap: 12 },
    half: { flex: 1, minWidth: 0 },
    chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 14 },
    chip: { flexShrink: 0, maxWidth: "100%", minHeight: 44, paddingHorizontal: 16, borderRadius: 22, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card, alignItems: "center", justifyContent: "center" },
    chipSelected: { backgroundColor: colors.brandSoft, borderColor: colors.brandPrimary },
    chipText: { color: colors.onSurfaceSecondary, fontSize: 13, fontWeight: "600", lineHeight: 18, flexShrink: 1 },
    chipSelectedText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "700", lineHeight: 18, flexShrink: 1 },
    stickyActions: { flexDirection: "row", gap: 10, marginTop: 24 },

    appHeader: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
    headerTitle: { color: colors.onSurface, fontSize: 26, lineHeight: 34, fontWeight: "800", letterSpacing: -0.4, marginTop: 5 },
    iconButton: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, flexShrink: 0 },
    screenContent: { alignSelf: "center", width: "100%", maxWidth: 620, padding: 20, paddingBottom: 40 },

    readinessCard: { borderRadius: radius.xl, padding: 22, backgroundColor: colors.hero, flexDirection: "row", justifyContent: "space-between", alignItems: "center", minHeight: 158, gap: 12, boxShadow: colors.shadowCard },
    cardEyebrow: { color: colors.accent, fontSize: 11, letterSpacing: 1.2, fontWeight: "700", lineHeight: 16 },
    cardEyebrowOnDark: { color: colors.onHero, opacity: 0.8, fontSize: 11, letterSpacing: 1.2, fontWeight: "700", lineHeight: 16 },
    readinessValue: { color: colors.onHero, fontSize: 46, lineHeight: 54, fontWeight: "800", marginTop: 6, fontVariant: ["tabular-nums"] },
    readinessSlash: { color: colors.onHero, opacity: 0.8, fontSize: 16, fontWeight: "500" },
    cardCaption: { color: colors.onHero, opacity: 0.8, fontSize: 13, lineHeight: 18, marginTop: 4 },
    readinessRing: { width: 92, height: 92, borderRadius: 46, borderWidth: 8, borderColor: colors.heroTrack, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    ringText: { color: colors.onHero, fontSize: 20, lineHeight: 24, fontWeight: "800", fontVariant: ["tabular-nums"] },
    ringCaption: { color: colors.onHero, opacity: 0.8, fontSize: 10, lineHeight: 13, marginTop: 3, textAlign: "center", paddingHorizontal: 6 },
    eatBanner: { backgroundColor: colors.brandSoft, borderRadius: 22, padding: 16, marginTop: 14, flexDirection: "row", alignItems: "center", gap: 12 },
    bannerIcon: { width: 46, height: 46, borderRadius: 15, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    bannerTitle: { color: colors.onBrandTertiary, fontSize: 16, fontWeight: "700", lineHeight: 22 },
    bannerSub: { color: colors.onBrandTertiary, opacity: 0.85, fontSize: 12, lineHeight: 17, marginTop: 3 },
    sectionHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 28, marginBottom: 12 },
    sectionTitleSmall: { color: colors.onSurface, fontSize: 19, lineHeight: 26, fontWeight: "800", letterSpacing: -0.2 },
    mutedText: { color: colors.muted, fontSize: 13, lineHeight: 19 },
    mealCard: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 10, borderWidth: 1, borderColor: colors.border, boxShadow: colors.shadowCard },
    mealDot: { width: 42, height: 42, borderRadius: 13, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    mealType: { color: colors.accent, fontSize: 10, letterSpacing: 1, fontWeight: "700", lineHeight: 14 },
    mealName: { color: colors.onSurface, fontSize: 15, fontWeight: "700", lineHeight: 20, marginTop: 3 },
    mealMeta: { color: colors.muted, fontSize: 12, lineHeight: 17, marginTop: 4 },
    logButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.card, alignItems: "center", justifyContent: "center", borderWidth: 1.5, borderColor: colors.brandPrimary, flexShrink: 0 },
    logButtonDone: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
    logRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border },
    editForm: { paddingTop: 10, gap: 4, borderTopWidth: 1, borderTopColor: colors.border },
    rowActions: { flexDirection: "row", gap: 8 },
    removeButton: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.borderStrong },
    logButtonText: { color: colors.brandPrimary, fontSize: 25, lineHeight: 27, fontWeight: "400" },
    reasonCard: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, padding: 17, borderRadius: radius.lg, marginTop: 12, boxShadow: colors.shadowCard },
    reasonText: { color: colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21, marginTop: 7 },
    dayRow: { gap: 8, paddingVertical: 6, paddingHorizontal: 2 },
    planIntro: { marginVertical: 14, padding: 16, backgroundColor: colors.brandFaint, borderRadius: 18 },
    planDay: { color: colors.onSurface, fontSize: 20, lineHeight: 27, fontWeight: "700" },

    syncCard: { flexDirection: "row", alignItems: "center", gap: 12, padding: 15, borderRadius: radius.lg, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, marginBottom: 26, boxShadow: colors.shadowCard },
    syncIcon: { width: 42, height: 42, borderRadius: 13, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    syncIconTint: { color: colors.brandPrimary },
    statusPill: { color: colors.success, fontSize: 11, fontWeight: "700", lineHeight: 15, backgroundColor: colors.brandFaint, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, flexShrink: 0 },
    activityHero: { flexDirection: "row", alignItems: "center", gap: 18, padding: 20, borderRadius: radius.lg, backgroundColor: colors.brandFaint, marginVertical: 16 },
    bigRing: { width: 106, height: 106, borderRadius: 53, borderWidth: 9, borderColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    bigRingValue: { color: colors.brandPrimary, fontSize: 22, lineHeight: 27, fontWeight: "700" },
    bigRingCaption: { color: colors.onSurfaceSecondary, fontSize: 11, lineHeight: 15, marginTop: 2 },
    successText: { color: colors.success, textAlign: "center", fontSize: 14, fontWeight: "700", lineHeight: 19, marginTop: 14 },

    chartCard: { padding: 18, borderRadius: radius.lg, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, marginTop: 8, boxShadow: colors.shadowCard },
    chart: { height: 154, flexDirection: "row", alignItems: "flex-end", gap: 12, borderBottomWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 8, paddingTop: 18, marginVertical: 14 },
    chartCol: { flex: 1, minWidth: 0, alignItems: "center", justifyContent: "flex-end", height: 130, gap: 6 },
    chartBar: { width: "72%", maxWidth: 34, borderRadius: 8, backgroundColor: colors.brandPrimary, minHeight: 12 },
    chartLabel: { color: colors.muted, fontSize: 10, lineHeight: 13 },
    inlineForm: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 14 },
    inlineInput: { flex: 1, minWidth: 0, minHeight: 52, borderRadius: 16, borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 16, color: colors.onSurface, backgroundColor: colors.card },
    placeholder: { color: colors.muted },
    wellnessNotice: { color: colors.muted, fontSize: 12, lineHeight: 17, paddingHorizontal: 20, paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surfaceSecondary },
    disclaimer: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 22 },

    chatContent: { flexGrow: 1, padding: 20, paddingBottom: 18, maxWidth: 620, width: "100%", alignSelf: "center" },
    coachBubble: { alignSelf: "flex-start", maxWidth: "88%", backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: 20, borderTopLeftRadius: 6, padding: 14, marginBottom: 12 },
    userBubble: { alignSelf: "flex-end", maxWidth: "88%", backgroundColor: colors.brandPrimary, borderRadius: 20, borderTopRightRadius: 6, padding: 14, marginBottom: 12 },
    coachBubbleText: { color: colors.onSurface, fontSize: 15, lineHeight: 22 },
    userBubbleText: { color: colors.onBrandPrimary, fontSize: 15, lineHeight: 22 },
    quickRow: { gap: 8, marginTop: 10 },
    durationRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 },
    chatComposer: { flexDirection: "row", gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: colors.divider, backgroundColor: colors.surface },
    chatInput: { flex: 1, minWidth: 0, minHeight: 48, borderRadius: 24, borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 18, color: colors.onSurface, backgroundColor: colors.card },
    sendButton: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center", backgroundColor: colors.brandPrimary, flexShrink: 0 },
    sendIcon: { color: colors.onBrandPrimary },

    recipeCard: { alignSelf: "flex-start", width: "100%", maxWidth: "100%", backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg, padding: 16, marginTop: -4, marginBottom: 12 },
    recipeTitle: { color: colors.onSurface, fontSize: 17, lineHeight: 23, fontWeight: "700", marginTop: 6 },
    recipeLabel: { color: colors.accent, fontSize: 11, letterSpacing: 1, fontWeight: "700", lineHeight: 16, marginTop: 14, marginBottom: 4 },
    recipeItem: { color: colors.onSurfaceSecondary, fontSize: 13, lineHeight: 20 },

    // Feedback pill: a small light card, centred and capped in width. The host spans the screen but lets taps through.
    toastHost: { position: "absolute", left: 16, right: 16, alignItems: "center", zIndex: 1000, elevation: 12 },
    toast: { flexDirection: "row", alignItems: "center", gap: 10, maxWidth: 420, minHeight: 48, paddingVertical: 8, paddingLeft: 12, paddingRight: 14, borderRadius: 24, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card, boxShadow: colors.shadowRaised },
    toastIcon: { width: 24, height: 24, borderRadius: 12, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    toastIconText: { fontSize: 14, lineHeight: 18, fontWeight: "800" },
    toastText: { flexShrink: 1, color: colors.onSurface, fontSize: 14, fontWeight: "600", lineHeight: 20 },
    toastAction: { minHeight: 32, paddingHorizontal: 10, marginLeft: 2, borderRadius: 16, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", flexShrink: 0 },
    toastActionText: { color: colors.brandPrimary, fontSize: 13, fontWeight: "800", lineHeight: 18 },

    // Log food: search box, suggestion rows and the serving sheet.
    searchBar: { flexDirection: "row", alignItems: "center", gap: 8, minHeight: 54, borderRadius: 27, borderWidth: 1, borderColor: colors.borderStrong, backgroundColor: colors.card, paddingLeft: 18, paddingRight: 8 },
    searchInput: { flex: 1, minWidth: 0, height: 50, color: colors.onSurface, fontSize: 16 },
    searchClear: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceTertiary },
    searchClearText: { color: colors.onSurfaceSecondary, fontSize: 16, lineHeight: 20, fontWeight: "700" },
    foodRow: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 64, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.divider },
    foodName: { color: colors.onSurface, fontSize: 16, fontWeight: "700", lineHeight: 22 },
    foodMeta: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 2 },
    foodAdd: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.card, alignItems: "center", justifyContent: "center", borderWidth: 1.5, borderColor: colors.brandPrimary, flexShrink: 0 },
    foodAddDone: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
    foodAddText: { color: colors.brandPrimary, fontSize: 25, lineHeight: 27 },
    foodAddDoneText: { color: colors.onBrandPrimary, fontSize: 20, lineHeight: 24, fontWeight: "800" },
    sheetBackdrop: { flex: 1, backgroundColor: colors.scrim, justifyContent: "flex-end", alignItems: "center" },
    sheet: { width: "100%", maxWidth: 520, backgroundColor: colors.card, borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 24, boxShadow: colors.shadowRaised },
    sheetHandle: { alignSelf: "center", width: 44, height: 5, borderRadius: 3, backgroundColor: colors.borderStrong, marginBottom: 12 },
    sheetTitle: { color: colors.onSurface, fontSize: 22, lineHeight: 29, fontWeight: "700" },
    stepperRow: { flexDirection: "row", alignItems: "center", gap: 14, marginTop: 4, marginBottom: 6 },
    stepperButton: { width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: colors.brandPrimary, backgroundColor: colors.card, alignItems: "center", justifyContent: "center" },
    stepperButtonText: { color: colors.brandPrimary, fontSize: 24, lineHeight: 28, fontWeight: "500" },
    stepperValue: { minWidth: 56, textAlign: "center", color: colors.onSurface, fontSize: 22, lineHeight: 28, fontWeight: "700" },
    totalsRow: { flexDirection: "row", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginTop: 14, marginBottom: 14, padding: 14, borderRadius: 18, backgroundColor: colors.brandFaint },
    totalKcal: { color: colors.brandPrimary, fontSize: 30, lineHeight: 36, fontWeight: "800", fontVariant: ["tabular-nums"] },
    totalMacro: { color: colors.onSurfaceSecondary, fontSize: 13, lineHeight: 20, fontWeight: "600" },
    categoryRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 4 },
    linkButton: { minHeight: 44, justifyContent: "center", alignSelf: "flex-start" },

    macroRow: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginVertical: 18 },
    macro: { color: colors.onSurfaceSecondary, backgroundColor: colors.surfaceTertiary, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, fontSize: 12, fontWeight: "600", lineHeight: 16 },
    modalTitle: { color: colors.onSurface, fontSize: 26, lineHeight: 34, fontWeight: "800", letterSpacing: -0.4, marginTop: 8 },
    modalMeal: { color: colors.brandPrimary, fontSize: 21, lineHeight: 28, fontWeight: "700", marginTop: 16 },
    modalSub: { color: colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21, marginTop: 7, marginBottom: 12 },
    settingRow: { flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: colors.divider },
    switchTrack: { width: 48, height: 28, padding: 3, borderRadius: 16, backgroundColor: colors.surfaceTertiary, justifyContent: "center", flexShrink: 0 },
    switchOn: { backgroundColor: colors.brandPrimary },
    switchKnob: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.onBrandPrimary, transform: [{ translateX: 0 }] },
    switchKnobOn: { transform: [{ translateX: 20 }] },

    photoPreview: { width: "100%", height: 230, borderRadius: radius.lg, overflow: "hidden", backgroundColor: colors.surfaceTertiary, marginTop: 16 },
    stickyCta: { padding: 16, borderTopWidth: 1, borderTopColor: colors.divider, backgroundColor: colors.surface },
    }),
    fonts,
  ),
);
