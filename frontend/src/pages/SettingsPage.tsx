import { Box, Typography, Paper, Grid, Switch, FormControlLabel, TextField, Button, Divider } from "@mui/material";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { useAuth } from "@/contexts/AuthContext";

export function SettingsPage() {
  const { palette, mode, toggleMode } = useThemeColors();
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Settings</Typography>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        Manage your profile, appearance, and security preferences.
      </Typography>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: "10px" }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 2 }}>Profile</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField label="Full name" size="small" defaultValue={user?.full_name ?? ""} fullWidth />
              <TextField label="Email" size="small" defaultValue={user?.email ?? ""} fullWidth disabled />
              <TextField label="Department" size="small" defaultValue={user?.department ?? ""} fullWidth />
              <TextField label="Region" size="small" defaultValue={user?.region ?? ""} fullWidth />
              <Button variant="contained" sx={{ alignSelf: "flex-start" }}>Save changes</Button>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: "10px", mb: 2.5 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1.5 }}>Appearance</Typography>
            <FormControlLabel
              control={<Switch checked={mode === "dark"} onChange={toggleMode} />}
              label={<Typography sx={{ fontSize: 13.5 }}>Dark mode</Typography>}
            />
          </Paper>

          <Paper sx={{ p: 3, borderRadius: "10px", mb: 2.5 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1.5 }}>Notifications</Typography>
            <FormControlLabel control={<Switch defaultChecked />} label={<Typography sx={{ fontSize: 13.5 }}>Critical equipment alerts</Typography>} />
            <br />
            <FormControlLabel control={<Switch defaultChecked />} label={<Typography sx={{ fontSize: 13.5 }}>New AI recommendations</Typography>} />
          </Paper>

          <Paper sx={{ p: 3, borderRadius: "10px" }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1.5 }}>Security</Typography>
            <Button size="small" variant="outlined">Change password</Button>
            <Divider sx={{ my: 2 }} />
            <Typography sx={{ fontSize: 12, color: palette.textSecondary }}>
              Role: <strong style={{ textTransform: "capitalize" }}>{user?.role}</strong>
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
