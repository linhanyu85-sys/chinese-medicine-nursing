import { Platform, type ViewStyle } from "react-native";

export const colors = {
  primary: "#23433b",
  secondary: "#556f67",
  accent: "#b95c36",
  accentSoft: "#e7c8b0",
  bamboo: "#6e8b74",
  bg: "#f6f0e6",
  bgSoft: "#fbf7f0",
  card: "#ffffff",
  text: "#2f312c",
  subText: "#756e63",
  danger: "#b04238",
  warning: "#b37a2a",
  success: "#3a7d58",
  border: "#dfd4c2",
  borderStrong: "#c8b89f",
  shadow: "rgba(60, 42, 23, 0.12)",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
};

export const typography = {
  title: {
    fontSize: 28 as const,
    fontWeight: "800" as const,
    lineHeight: 36 as const,
  },
  section: {
    fontSize: 18 as const,
    fontWeight: "700" as const,
    lineHeight: 24 as const,
  },
  body: {
    fontSize: 15 as const,
    lineHeight: 22 as const,
  },
};

function hexToRgba(color: string, opacity: number): string {
  const normalized = color.replace("#", "");
  if (normalized.length !== 6) {
    return color;
  }

  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

function shadowStyle(params: {
  color: string;
  opacity?: number;
  x?: number;
  y: number;
  blur: number;
  elevation: number;
}): ViewStyle {
  const opacity = params.opacity ?? 1;
  const x = params.x ?? 0;
  const webColor =
    params.color.startsWith("rgba(") || params.color.startsWith("hsla(")
      ? params.color
      : hexToRgba(params.color, opacity);

  if (Platform.OS === "web") {
    return {
      boxShadow: `${x}px ${params.y}px ${params.blur}px ${webColor}`,
    } as ViewStyle;
  }

  return {
    shadowColor: params.color,
    shadowOpacity: opacity,
    shadowRadius: params.blur,
    shadowOffset: { width: x, height: params.y },
    elevation: params.elevation,
  };
}

export const shadows = {
  hero: shadowStyle({
    color: colors.shadow,
    y: 10,
    blur: 20,
    elevation: 4,
  }),
  card: shadowStyle({
    color: colors.shadow,
    y: 8,
    blur: 14,
    elevation: 3,
  }),
  tabBar: shadowStyle({
    color: colors.shadow,
    y: 8,
    blur: 16,
    elevation: 6,
  }),
  floatingFab: shadowStyle({
    color: "#0f172a",
    opacity: 0.26,
    y: 7,
    blur: 12,
    elevation: 10,
  }),
  floatingPanel: shadowStyle({
    color: "#0f172a",
    opacity: 0.18,
    y: 8,
    blur: 12,
    elevation: 7,
  }),
};
