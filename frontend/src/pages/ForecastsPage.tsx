import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Typography, Paper, ToggleButtonGroup, ToggleButton, Grid, Skeleton } from "@mui/material";
import { forecastsApi } from "@/api/endpoints";
import { colors } from "@/theme/tokens";

type Granularity = "daily" | "weekly" | "monthly" | "quarterly";

function ForecastCard({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <Paper sx={{ p: 3, borderRadius: "12px" }}>
      <Typography sx={{ fontSize: 12.5, color: colors.textSecondary, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.03em" }}>
        {label}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.5 }}>
        <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 32, fontWeight: 700 }}>{value}</Typography>
        <Typography sx={{ fontSize: 13, color: colors.textSecondary }}>{unit}</Typography>
      </Box>
    </Paper>
  );
}

export function ForecastsPage() {
  const [granularity, setGranularity] = useState<Granularity>("weekly");

  const { data: demand, isLoading: demandLoading } = useQuery({
    queryKey: ["forecast-demand", granularity],
    queryFn: () => forecastsApi.getDemand(granularity),
  });

  const { data: revenue, isLoading: revenueLoading } = useQuery({
    queryKey: ["forecast-revenue", granularity === "daily" ? "weekly" : granularity],
    queryFn: () => forecastsApi.getRevenue(granularity === "daily" ? "weekly" : granularity),
  });

  const currency = (n: number) =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Forecasts</Typography>
      <Typography sx={{ color: colors.textSecondary, mb: 3, fontSize: 14 }}>
        AI-projected demand and revenue, trained on 18 months of seasonal rental history.
      </Typography>

      <ToggleButtonGroup
        value={granularity}
        exclusive
        onChange={(_, val) => val && setGranularity(val)}
        size="small"
        sx={{ mb: 3 }}
      >
        <ToggleButton value="daily">Daily</ToggleButton>
        <ToggleButton value="weekly">Weekly</ToggleButton>
        <ToggleButton value="monthly">Monthly</ToggleButton>
        <ToggleButton value="quarterly">Quarterly</ToggleButton>
      </ToggleButtonGroup>

      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6} md={4}>
          {demandLoading || !demand ? <Skeleton variant="rounded" height={100} /> : (
            <ForecastCard label={`${granularity} Demand`} value={demand.forecasted_demand.toFixed(1)} unit="rentals" />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          {revenueLoading || !revenue ? <Skeleton variant="rounded" height={100} /> : (
            <ForecastCard label="Revenue" value={currency(revenue.forecasted_revenue)} unit="" />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          {revenueLoading || !revenue ? <Skeleton variant="rounded" height={100} /> : (
            <ForecastCard label="Profit" value={currency(revenue.forecasted_profit)} unit="" />
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
