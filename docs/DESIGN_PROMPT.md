# Design run: a premium, responsive design system for every screen (mobile first, great on PC too)

Read CLAUDE.md and docs/PROGRESS.md. Run this only after the Logging run (docs/LOGGING_PROMPT.md) is merged, because
it touches the same screens. You are fully autonomous; ask me nothing unless a blocker only I can solve.
NEVER read, print or commit backend/.env or frontend/.env. Same loop as before: one branch and PR per item, tests
for each item (Playwright flows and screenshots at 3 sizes), tsc, ESLint, `npx expo-doctor` stays 20/20, web build,
squash-merge when green. Full pytest and full e2e once at the end, one after the other, never together (low memory).
Do not change behaviour or APIs: this run is visual and layout only (plus the small components it needs).

## Owner's brief
"Make it the best UI in the world: pleasant colours, real icons, enterprise-level UX on every tab. It must look
good on a phone AND on a PC (right now on PC it looks narrow and wrong)." Use the frontend-design skill's thinking:
a deliberate, distinctive aesthetic, not a generic template. Take inspiration from polished wellness apps for feel
only. Do NOT copy any competitor's layout, illustrations, copy or branding.

## Design direction (decide the details yourself, keep it coherent)
- Mood: calm, warm, premium, trustworthy health companion. Keep the brand anchors (deep sage green #4A6B5D, warm
  cream #FDFBF7) but build a full palette around them: a refined accent (for example warm terracotta/saffron for
  calories and highlights), semantic colours (success, warning, error), tinted neutrals, and macro colours
  (protein, carbs, fat, fibre) that stay distinguishable and meet WCAG AA contrast on their backgrounds.
- Design tokens in one place (src/theme.ts): colours for light AND dark mode (follow the system setting, plus a
  Settings override), spacing scale, radii, elevation/shadows (use boxShadow, not deprecated shadow* props), type
  scale, motion durations. No hard-coded colours or sizes in screens.
- Typography: one modern, readable open-licence family loaded properly (for example Inter or Plus Jakarta Sans
  via the expo-google-fonts packages) with a clear scale, tabular numbers for nutrition figures, and a matching
  Telugu font (Noto Sans Telugu) so Telugu looks as polished as English. Check licences and list them.
- Icons: a single consistent line-icon set (use @expo/vector-icons or lucide, whichever keeps expo-doctor 20/20).
  No emoji or placeholder squares as icons. Every meal slot, food category, tab, setting and action gets a proper
  icon. Add small, tasteful SVG illustrations for empty states and the welcome screen (original, drawn by you).
- Motion: subtle and fast (press feedback, list item enter, progress-ring and bar animations, sheet transitions);
  respect "reduce motion". Skeleton loaders instead of blank spinners.
- Components: build or refine a small library in src/components: Button (primary/secondary/ghost/destructive,
  sizes, loading state), Card, Chip, ProgressRing, MacroBar, Stat, ListRow, BottomSheet, Input with label/helper/
  error, SegmentedControl, EmptyState, Skeleton, Avatar, Badge, Toast (existing), Tabs. Touch targets at least 44 px.
- Accessibility: labels and roles, focus rings on web, keyboard navigation, contrast AA, font scaling that does not
  break layouts.

## Responsive layout (this is the PC fix)
- Phone (< 600 px): bottom tab bar, full-width content with proper safe areas.
- Tablet (600-1023 px): content centred with comfortable max width, bottom or side navigation.
- Desktop (>= 1024 px): a left sidebar with logo, icons and labels; main content in a centred max-width area
  (about 1100-1200 px) using a CSS-grid-like two or three column dashboard (for example Today: summary + meals
  on the left, insights, water, activity and coach shortcuts on the right). Modals and sheets become centred
  dialogs on desktop. Nothing stretches edge to edge or hugs the left side; toasts are anchored properly.
- Use a small useBreakpoint hook; avoid duplicating screens, adapt layouts.

## Items, in this order (one PR each)
1. Design tokens, dark mode, fonts, icon set, base components, breakpoint hook, desktop shell (sidebar) and phone shell.
2. Welcome, sign-in/sign-up, consent, forgot/reset/verify screens, and the multi-step onboarding including My Kitchen.
3. Today (hero summary ring with macros, meal slots with icons, quick actions, water, movement, suggestions).
4. Log food and the add sheet (search results with category icons, serving sheet, camera flow, confirm form).
5. Plan and shopping list (week strip, meal cards, swap sheet), and Eat-now.
6. Coach (modern chat UI: bubbles, typing indicator, suggestion cards such as "Suggest a low-carb lunch",
   "How was my day?", "Workout ideas", markdown-safe rendering, input bar).
7. Progress (clean charts for weight trend, calories vs target, protein and fibre, streaks; weekly review card).
8. Settings, My Kitchen, account screens, legal pages in-app, and the error/empty/offline states everywhere.

## Verify for each item
Take Playwright screenshots at 390x844 (phone), 820x1180 (tablet) and 1440x900 (desktop), light and dark, in English
and Telugu, and look at them yourself; fix overlaps, clipping, low contrast and awkward spacing before opening the PR.
Update e2e selectors if needed. Keep the existing testIDs where possible.

## Finish
Add a "Design run" section to docs/PROGRESS.md: the design system summary (palette, fonts, icons, breakpoints),
licences used, what is verified, what I must check on the phone, and what is not covered. Merge and stop.
After each PR note: files changed, tests added, what to verify.
