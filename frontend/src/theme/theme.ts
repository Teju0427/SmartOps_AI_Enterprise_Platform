import { createTheme, type Theme } from "@mui/material/styles";
import { lightPalette, darkPalette, brand, typography, type PaletteSet } from "./tokens";

export function buildTheme(mode: "light" | "dark"): Theme {
  const p: PaletteSet = mode === "dark" ? darkPalette : lightPalette;

  return createTheme({
    palette: {
      mode,
      primary: { main: brand.primary, dark: brand.primaryDark, contrastText: "#FFFFFF" },
      secondary: { main: brand.secondary },
      background: { default: p.bgDefault, paper: p.bgPaper },
      text: { primary: p.textPrimary, secondary: p.textSecondary },
      success: { main: brand.success },
      warning: { main: brand.warning },
      error: { main: brand.danger },
      info: { main: brand.info },
      divider: p.border,
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: typography.fontFamily,
      h1: { fontWeight: 700, letterSpacing: "-0.02em" },
      h2: { fontWeight: 700, letterSpacing: "-0.01em" },
      h3: { fontWeight: 600 },
      h4: { fontWeight: 600 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
      button: { fontWeight: 600, textTransform: "none" },
    },
    components: {
      MuiButton: { styleOverrides: { root: { borderRadius: 6, boxShadow: "none" } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
      MuiCard: {
        styleOverrides: {
          root: { border: `1px solid ${p.border}`, boxShadow: mode === "dark" ? "none" : "0 1px 2px rgba(20, 24, 31, 0.04)" },
        },
      },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTableCell: {
        styleOverrides: {
          head: { fontWeight: 700, fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.04em", color: p.textSecondary },
        },
      },
    },
  });
}
