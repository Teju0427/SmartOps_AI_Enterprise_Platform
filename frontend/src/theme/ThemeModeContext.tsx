import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { lightPalette, darkPalette, brand, statusColorMap, type PaletteSet } from "./tokens";

type Mode = "light" | "dark";

interface ThemeModeContextValue {
  mode: Mode;
  toggleMode: () => void;
  palette: PaletteSet;
  brand: typeof brand;
  statusColor: (status: string) => { fg: string; bg: string };
}

const ThemeModeContext = createContext<ThemeModeContextValue | undefined>(undefined);

const STORAGE_KEY = "smartops_theme_mode";

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "dark" || stored === "light" ? stored : "light";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const value = useMemo<ThemeModeContextValue>(() => {
    const palette = mode === "dark" ? darkPalette : lightPalette;
    return {
      mode,
      toggleMode: () => setMode((m) => (m === "light" ? "dark" : "light")),
      palette,
      brand,
      statusColor: (status: string) => {
        const entry = statusColorMap[status.toLowerCase()];
        if (!entry) return { fg: palette.textSecondary, bg: palette.border };
        return { fg: entry.fg, bg: mode === "dark" ? entry.bgDark : entry.bg };
      },
    };
  }, [mode]);

  return <ThemeModeContext.Provider value={value}>{children}</ThemeModeContext.Provider>;
}

export function useThemeColors(): ThemeModeContextValue {
  const ctx = useContext(ThemeModeContext);
  if (!ctx) throw new Error("useThemeColors must be used within ThemeModeProvider");
  return ctx;
}
