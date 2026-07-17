import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { buildTheme } from "@/theme/theme";
import { ThemeModeProvider, useThemeColors } from "@/theme/ThemeModeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/layouts/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EquipmentPage } from "@/pages/EquipmentPage";
import { DecisionsPage } from "@/pages/DecisionsPage";
import { MaintenancePage } from "@/pages/MaintenancePage";
import { CustomersPage } from "@/pages/CustomersPage";
import { ForecastsPage } from "@/pages/ForecastsPage";
import { PricingPage } from "@/pages/PricingPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { SettingsPage } from "@/pages/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

function ThemedApp() {
  const { mode } = useThemeColors();
  const theme = buildTheme(mode);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="equipment" element={<EquipmentPage />} />
              <Route path="decisions" element={<DecisionsPage />} />
              <Route path="maintenance" element={<MaintenancePage />} />
              <Route path="customers" element={<CustomersPage />} />
              <Route path="forecasts" element={<ForecastsPage />} />
              <Route path="pricing" element={<PricingPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <ThemedApp />
      </ThemeModeProvider>
    </QueryClientProvider>
  );
}
