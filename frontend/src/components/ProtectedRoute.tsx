import { Navigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "@/contexts/AuthContext";
import { colors } from "@/theme/tokens";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: colors.surface }}>
        <CircularProgress sx={{ color: colors.amber500 }} />
      </Box>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
