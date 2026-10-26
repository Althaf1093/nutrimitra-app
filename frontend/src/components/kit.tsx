import { useEffect, type ReactNode } from "react";
import {
  Pressable,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle } from "react-native-svg";

import { AppIcon, type IconName } from "@/src/components/icon";
import { makeStyles, motion, radius, space, useTheme } from "@/src/theme";

// The small component library every screen is built from. Colours, radii, spacing and motion all come from src/theme.ts.

const useKit = makeStyles((colors) => ({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
    boxShadow: colors.shadowCard,
  },
  cardSoft: {
    backgroundColor: colors.brandFaint,
    borderRadius: radius.lg,
    padding: space.lg,
  },
  cardHero: {
    backgroundColor: colors.hero,
    borderRadius: radius.xl,
    padding: 22,
    boxShadow: colors.shadowCard,
  },
  sectionRow: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: space.md,
    marginTop: space.xl,
    marginBottom: space.md,
  },
  sectionTitle: {
    flex: 1,
    minWidth: 0,
    color: colors.onSurface,
    fontSize: 19,
    lineHeight: 26,
    fontWeight: "800",
    letterSpacing: -0.2,
  },
  sectionAction: {
    color: colors.brandPrimary,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700",
  },
  actionHit: { minHeight: 44, justifyContent: "center" },
  ringCenter: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  macroTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    gap: 6,
  },
  macroLabel: { fontSize: 11, lineHeight: 16, fontWeight: "600" },
  macroValue: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  macroUnit: { fontSize: 11, lineHeight: 16, fontWeight: "600" },
  barTrack: { height: 6, borderRadius: 3, marginTop: 6, overflow: "hidden" },
  barFill: { height: 6, borderRadius: 3 },
  stat: { flex: 1, minWidth: 0, gap: 6 },
  statHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  statLabel: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700",
    flexShrink: 1,
  },
  statValue: {
    color: colors.onSurface,
    fontSize: 24,
    lineHeight: 30,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  statUnit: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "600",
  },
  listRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    minHeight: 56,
    paddingVertical: space.sm,
  },
  listIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  listTitle: {
    color: colors.onSurface,
    fontSize: 15,
    lineHeight: 21,
    fontWeight: "700",
  },
  listSub: { color: colors.muted, fontSize: 12, lineHeight: 17, marginTop: 2 },
  empty: {
    alignItems: "center",
    paddingVertical: 28,
    paddingHorizontal: space.xl,
    gap: space.sm,
  },
  emptyArt: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: space.sm,
  },
  emptyArtRing: {
    position: "absolute",
    width: 112,
    height: 112,
    borderRadius: 56,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderStyle: "dashed",
  },
  emptyTitle: {
    color: colors.onSurface,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: "800",
    textAlign: "center",
  },
  emptyBody: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
    maxWidth: 340,
  },
  avatar: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.brandSoft,
  },
  avatarText: { color: colors.brandPrimary, fontWeight: "800" },
  badge: {
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  badgeText: { fontSize: 11, lineHeight: 15, fontWeight: "700" },
  segment: {
    flexDirection: "row",
    backgroundColor: colors.surfaceTertiary,
    borderRadius: radius.pill,
    padding: 4,
  },
  segmentItem: {
    flex: 1,
    minWidth: 0,
    minHeight: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    paddingHorizontal: space.sm,
  },
  segmentItemOn: { backgroundColor: colors.card, boxShadow: colors.shadowCard },
  segmentText: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  segmentTextOn: { color: colors.onSurface, fontWeight: "700" },
  iconButton: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  scrim: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    backgroundColor: colors.scrim,
  },
}));

type Tone = "default" | "soft" | "hero";

export function Card({
  children,
  tone = "default",
  style,
  testID,
}: {
  children: ReactNode;
  tone?: Tone;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}) {
  const styles = useKit();
  return (
    <View
      testID={testID}
      style={[
        tone === "hero"
          ? styles.cardHero
          : tone === "soft"
            ? styles.cardSoft
            : styles.card,
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function SectionHeader({
  title,
  action,
  onAction,
  testID,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
  testID?: string;
}) {
  const styles = useKit();
  return (
    <View style={styles.sectionRow}>
      <Text accessibilityRole="header" style={styles.sectionTitle}>
        {title}
      </Text>
      {action && onAction ? (
        <Pressable
          testID={testID}
          accessibilityRole="button"
          onPress={onAction}
          style={styles.actionHit}
          hitSlop={6}
        >
          <Text style={styles.sectionAction}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** A circular progress ring. `value / max` fills it (never past full); the fill eases in unless the device asks for reduced motion. */
export function ProgressRing({
  value,
  max,
  size = 132,
  stroke = 12,
  color,
  track,
  children,
  testID,
}: {
  value: number;
  max: number;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  children?: ReactNode;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const radiusPx = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radiusPx;
  const fraction = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  const progress = useSharedValue(reduced ? fraction : 0);
  useEffect(() => {
    progress.value = reduced
      ? fraction
      : withTiming(fraction, {
          duration: motion.slow * 2,
          easing: Easing.out(Easing.cubic),
        });
  }, [fraction, reduced, progress]);
  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: circumference * (1 - progress.value),
  }));
  return (
    <View
      testID={testID}
      accessibilityRole="progressbar"
      accessibilityValue={{
        min: 0,
        max: Math.round(max),
        now: Math.round(Math.min(value, max)),
      }}
      style={{ width: size, height: size }}
    >
      <Svg
        width={size}
        height={size}
        style={{ transform: [{ rotate: "-90deg" }] }}
      >
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radiusPx}
          stroke={track ?? colors.heroTrack}
          strokeWidth={stroke}
          fill="none"
        />
        <AnimatedCircle
          cx={size / 2}
          cy={size / 2}
          r={radiusPx}
          stroke={color ?? colors.heroAccent}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={`${circumference} ${circumference}`}
          animatedProps={animatedProps}
        />
      </Svg>
      <View style={styles.ringCenter}>{children}</View>
    </View>
  );
}

/** One macro: a label, "58/110 g" and a bar. `onHero` draws it for the green summary card. */
export function MacroBar({
  label,
  value,
  target,
  unit = "g",
  color,
  onHero = false,
  noData = false,
  noDataText,
  testID,
}: {
  label: string;
  value: number;
  target: number;
  unit?: string;
  color: string;
  onHero?: boolean;
  noData?: boolean;
  noDataText?: string;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  const text = onHero ? colors.onHero : colors.onSurface;
  const soft = onHero ? colors.onHero : colors.muted;
  const fraction = noData
    ? 0
    : target > 0
      ? Math.max(0, Math.min(1, value / target))
      : 0;
  return (
    <View testID={testID} style={{ flex: 1, minWidth: 0 }}>
      <Text
        style={[styles.macroLabel, { color: soft, opacity: onHero ? 0.85 : 1 }]}
      >
        {label}
      </Text>
      {noData && noDataText ? (
        <Text
          style={[styles.macroUnit, { color: soft, opacity: 0.85 }]}
          numberOfLines={2}
        >
          {noDataText}
        </Text>
      ) : (
        <Text style={[styles.macroValue, { color: text }]}>
          {noData ? "—" : Math.round(value)}
          <Text style={[styles.macroUnit, { color: soft, opacity: 0.85 }]}>
            /{Math.round(target)} {unit}
          </Text>
        </Text>
      )}
      <View
        style={[
          styles.barTrack,
          {
            backgroundColor: onHero ? colors.heroTrack : colors.surfaceTertiary,
          },
        ]}
      >
        <View
          style={[
            styles.barFill,
            { width: `${Math.round(fraction * 100)}%`, backgroundColor: color },
          ]}
        />
      </View>
    </View>
  );
}

export function Stat({
  label,
  value,
  unit,
  icon,
  iconColor,
  children,
  testID,
}: {
  label: string;
  value: string | number;
  unit?: string;
  icon?: IconName;
  iconColor?: string;
  children?: ReactNode;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  return (
    <View testID={testID} style={styles.stat}>
      <View style={styles.statHead}>
        {icon ? (
          <AppIcon
            name={icon}
            size={18}
            color={iconColor ?? colors.brandPrimary}
          />
        ) : null}
        <Text style={styles.statLabel}>{label}</Text>
      </View>
      <Text style={styles.statValue}>
        {value}
        {unit ? <Text style={styles.statUnit}> {unit}</Text> : null}
      </Text>
      {children}
    </View>
  );
}

export function ListRow({
  icon,
  tint,
  tintSoft,
  title,
  subtitle,
  right,
  onPress,
  testID,
}: {
  icon?: IconName;
  tint?: string;
  tintSoft?: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
  onPress?: () => void;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  const body = (
    <>
      {icon ? (
        <View
          style={[
            styles.listIcon,
            { backgroundColor: tintSoft ?? colors.brandSoft },
          ]}
        >
          <AppIcon name={icon} size={22} color={tint ?? colors.brandPrimary} />
        </View>
      ) : null}
      <View style={{ flex: 1, minWidth: 0 }}>
        <Text style={styles.listTitle}>{title}</Text>
        {subtitle ? <Text style={styles.listSub}>{subtitle}</Text> : null}
      </View>
      {right ??
        (onPress ? (
          <AppIcon name="next" size={18} color={colors.muted} />
        ) : null)}
    </>
  );
  return onPress ? (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      onPress={onPress}
      style={({ pressed }) => [styles.listRow, pressed && { opacity: 0.75 }]}
    >
      {body}
    </Pressable>
  ) : (
    <View testID={testID} style={styles.listRow}>
      {body}
    </View>
  );
}

/** A friendly empty state: an icon in a soft circle, a title, a sentence and an optional action. */
export function EmptyState({
  icon = "leaf",
  title,
  body,
  children,
  testID,
}: {
  icon?: IconName;
  title: string;
  body?: string;
  children?: ReactNode;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  return (
    <View testID={testID} style={styles.empty}>
      <View style={styles.emptyArt}>
        <View style={styles.emptyArtRing} />
        <AppIcon
          name={icon}
          size={38}
          color={colors.brandPrimary}
          strokeWidth={1.6}
        />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      {body ? <Text style={styles.emptyBody}>{body}</Text> : null}
      {children}
    </View>
  );
}

/** A placeholder block that pulses softly while content loads (it stays still when the device asks for reduced motion). */
export function Skeleton({
  width = "100%",
  height = 16,
  rounded = 8,
  style,
}: {
  width?: number | `${number}%`;
  height?: number;
  rounded?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const opacity = useSharedValue(1);
  useEffect(() => {
    if (reduced) return;
    opacity.value = withRepeat(
      withSequence(
        withTiming(0.55, { duration: 700 }),
        withTiming(1, { duration: 700 }),
      ),
      -1,
    );
  }, [reduced, opacity]);
  const animated = useAnimatedStyle(() => ({ opacity: opacity.value }));
  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[
        {
          width,
          height,
          borderRadius: rounded,
          backgroundColor: colors.surfaceTertiary,
        },
        animated,
        style,
      ]}
    />
  );
}

export function Avatar({ name, size = 44 }: { name: string; size?: number }) {
  const styles = useKit();
  const initial = (name.trim()[0] ?? "?").toUpperCase();
  return (
    <View
      accessibilityElementsHidden
      style={[
        styles.avatar,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text
        style={[
          styles.avatarText,
          {
            fontSize: Math.round(size * 0.4),
            lineHeight: Math.round(size * 0.5),
          },
        ]}
      >
        {initial}
      </Text>
    </View>
  );
}

export function Badge({
  text,
  tone = "brand",
  icon,
  testID,
}: {
  text: string;
  tone?: "brand" | "accent" | "success" | "warning" | "error";
  icon?: IconName;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  const palette = {
    brand: [colors.brandSoft, colors.brandPrimary],
    accent: [colors.accentSoft, colors.accent],
    success: [colors.brandFaint, colors.success],
    warning: [colors.accentSoft, colors.warning],
    error: [colors.macroFatSoft, colors.error],
  }[tone];
  return (
    <View
      testID={testID}
      style={[
        styles.badge,
        {
          backgroundColor: palette[0],
          flexDirection: "row",
          alignItems: "center",
          gap: 4,
        },
      ]}
    >
      {icon ? (
        <AppIcon name={icon} size={12} color={palette[1]} strokeWidth={2.2} />
      ) : null}
      <Text style={[styles.badgeText, { color: palette[1] }]}>{text}</Text>
    </View>
  );
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  testID,
}: {
  options: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
  testID?: string;
}) {
  const styles = useKit();
  return (
    <View testID={testID} accessibilityRole="tablist" style={styles.segment}>
      {options.map((option) => (
        <Pressable
          key={option.id}
          testID={`${testID ?? "segment"}-${option.id}`}
          accessibilityRole="tab"
          accessibilityState={{ selected: value === option.id }}
          onPress={() => onChange(option.id)}
          style={[
            styles.segmentItem,
            value === option.id && styles.segmentItemOn,
          ]}
        >
          <Text
            style={[
              styles.segmentText,
              value === option.id && styles.segmentTextOn,
            ]}
          >
            {option.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

/** A round icon-only button with a 44 px touch target and a label for screen readers. */
export function IconButton({
  icon,
  label,
  onPress,
  size = 44,
  testID,
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
  size?: number;
  testID?: string;
}) {
  const styles = useKit();
  const { colors } = useTheme();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={4}
      style={({ pressed }) => [
        styles.iconButton,
        {
          width: Math.max(size, 44),
          height: Math.max(size, 44),
          borderRadius: Math.max(size, 44) / 2,
        },
        pressed && { opacity: 0.75 },
      ]}
    >
      <AppIcon
        name={icon}
        size={Math.round(size * 0.5)}
        color={colors.onSurface}
      />
    </Pressable>
  );
}
