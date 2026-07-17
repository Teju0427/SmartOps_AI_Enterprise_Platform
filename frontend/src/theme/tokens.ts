/**
 * SmartOps AI Enterprise Design Tokens.
 *
 * Palette direction: Deep Blue primary / Slate Gray secondary, matching
 * the Azure Portal / Power BI / enterprise-ERP register this product is
 * meant to sit in - deliberately restrained, no gradients, no
 * glassmorphism. Both light and dark variants are first-class (not a
 * dark mode bolted on afterward), since the toggle is a stated
 * requirement.
 */

export interface PaletteSet {
  mode: "light" | "dark";
  bgDefault: string;
  bgPaper: string;
  bgSidebar: string;
  bgSidebarActive: string;
  border: string;
  textPrimary: string;
  textSecondary: string;
  textOnSidebar: string;
  textOnSidebarMuted: string;
}

export const lightPalette: PaletteSet = {
  mode: "light",
  bgDefault: "#F4F6F9",
  bgPaper: "#FFFFFF",
  bgSidebar: "#0F2A47",
  bgSidebarActive: "#173C63",
  border: "#DDE3EA",
  textPrimary: "#16233A",
  textSecondary: "#5B6B82",
  textOnSidebar: "#EEF2F7",
  textOnSidebarMuted: "#93A5BE",
};

export const darkPalette: PaletteSet = {
  mode: "dark",
  bgDefault: "#0D1420",
  bgPaper: "#141C2B",
  bgSidebar: "#0A1421",
  bgSidebarActive: "#17253A",
  border: "#232F42",
  textPrimary: "#E8ECF2",
  textSecondary: "#8C9AB3",
  textOnSidebar: "#E8ECF2",
  textOnSidebarMuted: "#7387A6",
};

// Semantic brand + status colors - identical across light/dark so status
// meaning never shifts with theme.
export const brand = {
  primary: "#1F4E8C", // deep blue
  primaryDark: "#163B6B",
  secondary: "#5B6B82", // slate gray
  success: "#1E8E5A", // emerald
  warning: "#C7861A", // amber
  danger: "#C43D3D", // red
  info: "#2E72B8", // blue
} as const;

export const statusColorMap: Record<string, { fg: string; bg: string; bgDark: string }> = {
  healthy: { fg: brand.success, bg: "#E4F5EC", bgDark: "#12291F" },
  warning: { fg: brand.warning, bg: "#FBF0DC", bgDark: "#2E230F" },
  critical: { fg: brand.danger, bg: "#FBE6E6", bgDark: "#2E1414" },
  low: { fg: brand.success, bg: "#E4F5EC", bgDark: "#12291F" },
  medium: { fg: brand.warning, bg: "#FBF0DC", bgDark: "#2E230F" },
  high: { fg: brand.danger, bg: "#FBE6E6", bgDark: "#2E1414" },
};

export const typography = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontFamilyMono: "'JetBrains Mono', 'SF Mono', Consolas, monospace",
} as const;

export const chartPalette = [brand.primary, brand.info, brand.success, brand.warning, "#7A6BA8", "#3E8F87"];

// ---------------------------------------------------------------------
// Backward-compatible static export. Pages not yet migrated to the new
// useThemeColors() hook still import `colors` directly - this keeps them
// compiling (light-mode values) while each page is migrated one at a
// time per the incremental redesign plan. Remove once every page uses
// the hook.
// ---------------------------------------------------------------------
export const colors = {
  graphite900: lightPalette.bgSidebar,
  graphite800: lightPalette.bgSidebarActive,
  graphite700: lightPalette.bgSidebarActive,
  graphite600: "#2F4867",
  surface: lightPalette.bgDefault,
  surfaceCard: lightPalette.bgPaper,
  border: lightPalette.border,
  textPrimary: lightPalette.textPrimary,
  textSecondary: lightPalette.textSecondary,
  textOnDark: lightPalette.textOnSidebar,
  textOnDarkMuted: lightPalette.textOnSidebarMuted,
  amber500: brand.warning,
  amber600: "#A5690F",
  amber100: "#FBF0DC",
  healthy: brand.success,
  healthyBg: statusColorMap.healthy.bg,
  warning: brand.warning,
  warningBg: statusColorMap.warning.bg,
  critical: brand.danger,
  criticalBg: statusColorMap.critical.bg,
  chartBlue: brand.info,
  chartTeal: "#3E8F87",
  chartPurple: "#7A6BA8",
} as const;

export const radii = { sm: 6, md: 10, lg: 16 } as const;
