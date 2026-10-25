import { useWindowDimensions } from "react-native";

import { layout } from "@/src/theme";

export type Breakpoint = "phone" | "tablet" | "desktop";

export function breakpointFor(width: number): Breakpoint {
  return width >= layout.desktopMin ? "desktop" : width >= layout.tabletMin ? "tablet" : "phone";
}

/** phone (< 600), tablet (600 to 1023) or desktop (1024 and up), updated as the window is resized. */
export function useBreakpoint() {
  const { width, height } = useWindowDimensions();
  const breakpoint = breakpointFor(width);
  return { breakpoint, width, height, isPhone: breakpoint === "phone", isTablet: breakpoint === "tablet", isDesktop: breakpoint === "desktop" };
}
