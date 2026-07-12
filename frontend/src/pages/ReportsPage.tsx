import { Box, Typography, Paper, Button, Grid } from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { useThemeColors } from "@/theme/ThemeModeContext";

const REPORTS = [
  { title: "Revenue Report", desc: "Historical revenue, profit, and margin breakdown by period." },
  { title: "Equipment Report", desc: "Fleet health, utilization, and status across all machines." },
  { title: "Maintenance Report", desc: "Completed and scheduled maintenance with cost analysis." },
  { title: "Forecast Report", desc: "Demand and revenue projections with confidence intervals." },
  { title: "Customer Analytics", desc: "Lifetime value, payment risk, and industry breakdown." },
];

export function ReportsPage() {
  const { palette } = useThemeColors();

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Reports</Typography>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        Generate and export operational reports across the platform.
      </Typography>

      <Grid container spacing={2.5}>
        {REPORTS.map((r) => (
          <Grid item xs={12} sm={6} md={4} key={r.title}>
            <Paper sx={{ p: 2.5, borderRadius: "10px", height: "100%", display: "flex", flexDirection: "column" }}>
              <Typography sx={{ fontWeight: 700, fontSize: 15, mb: 0.5 }}>{r.title}</Typography>
              <Typography sx={{ fontSize: 13, color: palette.textSecondary, flexGrow: 1, mb: 2 }}>{r.desc}</Typography>
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button size="small" variant="outlined" startIcon={<DownloadOutlinedIcon />}>CSV</Button>
                <Button size="small" variant="outlined" startIcon={<DownloadOutlinedIcon />}>PDF</Button>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
