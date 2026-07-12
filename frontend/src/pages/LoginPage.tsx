import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Paper, TextField, Button, Typography, Alert, Checkbox,
  FormControlLabel, IconButton, InputAdornment, Link, CircularProgress,
} from "@mui/material";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { useAuth } from "@/contexts/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { palette, brand } = useThemeColors();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Incorrect email or password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "stretch",
        bgcolor: palette.bgDefault,
      }}
    >
      {/* Left panel - branding / value proposition (hidden on small screens) */}
      <Box
        sx={{
          flex: 1,
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "center",
          px: 8,
          bgcolor: palette.bgSidebar,
          color: palette.textOnSidebar,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 4 }}>
          <Box
            sx={{
              width: 40, height: 40, borderRadius: "8px", bgcolor: brand.primary,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <InsightsOutlinedIcon sx={{ color: "#FFFFFF", fontSize: 22 }} />
          </Box>
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: 20, lineHeight: 1.1 }}>RentalIQ</Typography>
            <Typography sx={{ fontSize: 12, color: palette.textOnSidebarMuted }}>
              Enterprise AI Rental Intelligence Platform
            </Typography>
          </Box>
        </Box>

        <Typography sx={{ fontSize: 28, fontWeight: 700, lineHeight: 1.3, maxWidth: 440 }}>
          Predictive intelligence for your entire equipment fleet.
        </Typography>
        <Typography sx={{ fontSize: 14.5, color: palette.textOnSidebarMuted, mt: 2, maxWidth: 420, lineHeight: 1.7 }}>
          Real-time health scoring, failure prediction, dynamic pricing, and
          demand forecasting — powered by machine learning models trained on
          your fleet's actual operating data.
        </Typography>
      </Box>

      {/* Right panel - login form */}
      <Box sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", px: 3 }}>
        <Box sx={{ width: "100%", maxWidth: 400 }}>
          <Paper sx={{ p: 4.5, borderRadius: "12px" }}>
            <Box sx={{ display: { xs: "flex", md: "none" }, alignItems: "center", gap: 1.25, mb: 3 }}>
              <Box
                sx={{
                  width: 34, height: 34, borderRadius: "7px", bgcolor: brand.primary,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                <InsightsOutlinedIcon sx={{ color: "#FFFFFF", fontSize: 19 }} />
              </Box>
              <Typography sx={{ fontWeight: 700, fontSize: 18 }}>RentalIQ</Typography>
            </Box>

            <Typography sx={{ fontWeight: 700, fontSize: 22, mb: 0.5 }}>Welcome back</Typography>
            <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
              Sign in to your fleet intelligence dashboard.
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2.5 }}>{error}</Alert>}

            <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="Email address" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)}
                required fullWidth size="small" autoFocus
              />
              <TextField
                label="Password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required fullWidth size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowPassword((s) => !s)} edge="end" size="small" tabIndex={-1}>
                        {showPassword ? <VisibilityOffOutlinedIcon fontSize="small" /> : <VisibilityOutlinedIcon fontSize="small" />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mt: -1 }}>
                <FormControlLabel
                  control={<Checkbox size="small" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />}
                  label={<Typography sx={{ fontSize: 13 }}>Remember me</Typography>}
                />
                <Link href="#" sx={{ fontSize: 13, fontWeight: 600 }} underline="hover">
                  Forgot password?
                </Link>
              </Box>

              <Button type="submit" variant="contained" disabled={loading} sx={{ py: 1.2, mt: 1 }}>
                {loading ? <CircularProgress size={20} sx={{ color: "#FFFFFF" }} /> : "Sign in"}
              </Button>
            </Box>
          </Paper>

          <Typography sx={{ textAlign: "center", fontSize: 12, color: palette.textSecondary, mt: 3 }}>
            Powered by React · FastAPI · PostgreSQL · Machine Learning
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
