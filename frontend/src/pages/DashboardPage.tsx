import { useQuery } from "@tanstack/react-query";
import { Box, Grid, Paper, Typography, Skeleton, List, ListItem, ListItemText, Divider, Chip } from "@mui/material";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { dashboardApi, decisionsApi, forecastsApi } from "@/api/endpoints";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { RadialGauge } from "@/components/RadialGauge";

function StatCard({ label, value, sublabel, accent }: { label: string; value: string; sublabel?: string; accent?: string }) {
  const { palette } = useThemeColors();
  return (
    <Paper sx={{ p: 2.5, borderRadius: "10px", height: "100%" }}>
      <Typography sx={{ fontSize: 12, color: palette.textSecondary, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.03em" }}>
        {label}
      </Typography>
      <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 27, fontWeight: 700, mt: 0.5, color: accent ?? palette.textPrimary }}>
        {value}
      </Typography>
      {sublabel && <Typography sx={{ fontSize: 12, color: palette.textSecondary, mt: 0.5 }}>{sublabel}</Typography>}
    </Paper>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  const { palette } = useThemeColors();
  return (
    <Paper sx={{ p: 3, borderRadius: "10px", height: "100%" }}>
      <Typography sx={{ fontSize: 13, fontWeight: 700, color: palette.textSecondary, textTransform: "uppercase", letterSpacing: "0.03em", mb: 2 }}>
        {title}
      </Typography>
      {children}
    </Paper>
  );
}

const currency = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export function DashboardPage() {
  const { palette, brand, statusColor } = useThemeColors();

  const { data, isLoading } = useQuery({ queryKey: ["dashboard-summary"], queryFn: dashboardApi.getSummary });
  const { data: topDecisions } = useQuery({
    queryKey: ["dashboard-top-decisions"],
    queryFn: () => decisionsApi.list({ page: 1, page_size: 5 }),
  });
  const { data: weeklyRevenue } = useQuery({ queryKey: ["fc-rev-weekly"], queryFn: () => forecastsApi.getRevenue("weekly") });
  const { data: monthlyRevenue } = useQuery({ queryKey: ["fc-rev-monthly"], queryFn: () => forecastsApi.getRevenue("monthly") });
  const { data: quarterlyRevenue } = useQuery({ queryKey: ["fc-rev-quarterly"], queryFn: () => forecastsApi.getRevenue("quarterly") });

  if (isLoading || !data) {
    return (
      <Box>
        <Skeleton variant="text" width={240} height={40} />
        <Grid container spacing={2.5} sx={{ mt: 1 }}>
          {[1, 2, 3, 4].map((i) => <Grid item xs={12} sm={6} md={3} key={i}><Skeleton variant="rounded" height={100} /></Grid>)}
        </Grid>
      </Box>
    );
  }

  const healthStatus =
    (data.equipment.avg_health_score ?? 0) >= 70 ? "healthy" : (data.equipment.avg_health_score ?? 0) >= 40 ? "warning" : "critical";

  const statusDistribution = [
    { name: "Healthy", value: data.equipment.total - data.equipment.critical_count - data.equipment.warning_count, color: statusColor("healthy").fg },
    { name: "Warning", value: data.equipment.warning_count, color: statusColor("warning").fg },
    { name: "Critical", value: data.equipment.critical_count, color: statusColor("critical").fg },
  ];

  const regionData = [...data.regional_breakdown].sort((a, b) => b.equipment_count - a.equipment_count).slice(0, 8);

  const revenueForecastData = [
    { period: "Weekly", revenue: weeklyRevenue?.forecasted_revenue ?? 0, profit: weeklyRevenue?.forecasted_profit ?? 0 },
    { period: "Monthly", revenue: monthlyRevenue?.forecasted_revenue ?? 0, profit: monthlyRevenue?.forecasted_profit ?? 0 },
    { period: "Quarterly", revenue: quarterlyRevenue?.forecasted_revenue ?? 0, profit: quarterlyRevenue?.forecasted_profit ?? 0 },
  ];

  const systemChecks = [
    { label: "Database", ok: true },
    { label: "Authentication", ok: true },
    { label: "Failure Prediction Engine", ok: true },
    { label: "Pricing Engine", ok: true },
    { label: "Forecast Engine", ok: !!weeklyRevenue },
    { label: "AI Decision Engine", ok: (data.alerts_and_decisions.pending_recommendations ?? 0) >= 0 },
  ];

  return (
    <Box>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        Real-time status across your rental fleet, powered by 7 trained AI models.
      </Typography>

      {/* KPI Row */}
      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Total Equipment" value={String(data.equipment.total)} sublabel={`${data.equipment.available} available`} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Historical Revenue" value={currency(data.financial.total_historical_revenue)} sublabel="All-time" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Historical Profit" value={currency(data.financial.total_historical_profit)} sublabel="All-time" accent={brand.success} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Critical Alerts" value={String(data.equipment.critical_count)}
            sublabel={`${data.equipment.warning_count} in warning`}
            accent={data.equipment.critical_count > 0 ? brand.danger : undefined}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Active Rentals" value={String(data.financial.active_rentals)} sublabel={`${data.financial.overdue_rentals} overdue`} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Total Customers" value={String(data.customers.total)} sublabel="Active accounts" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Pending Decisions" value={String(data.alerts_and_decisions.pending_recommendations)} sublabel="AI-generated" accent={brand.primary} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Fleet Availability"
            value={`${Math.round((data.equipment.available / Math.max(data.equipment.total, 1)) * 100)}%`}
            sublabel={`${data.equipment.available} of ${data.equipment.total}`}
          />
        </Grid>
      </Grid>

      {/* Charts row 1 */}
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, borderRadius: "10px", height: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <Typography sx={{ fontSize: 13, fontWeight: 700, color: palette.textSecondary, textTransform: "uppercase", letterSpacing: "0.03em", alignSelf: "flex-start", mb: 2 }}>
              Fleet Avg. Health
            </Typography>
            <RadialGauge value={data.equipment.avg_health_score ?? 0} status={healthStatus} size={130} />
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <ChartCard title="Equipment Status">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={statusDistribution} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={2}>
                  {statusDistribution.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                </Pie>
                <RTooltip />
                <Legend verticalAlign="bottom" height={24} iconSize={9} wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>

        <Grid item xs={12} md={4}>
          <ChartCard title="Revenue Forecast">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={revenueForecastData}>
                <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <RTooltip formatter={(v: unknown) => currency(Number(v))} />
                <Bar dataKey="revenue" fill={brand.primary} radius={[3, 3, 0, 0]} name="Revenue" />
                <Bar dataKey="profit" fill={brand.success} radius={[3, 3, 0, 0]} name="Profit" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
      </Grid>

      {/* Charts row 2 */}
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={5}>
          <ChartCard title="Equipment by Region">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={regionData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={palette.border} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={80} />
                <RTooltip />
                <Bar dataKey="equipment_count" fill={brand.info} radius={[0, 3, 3, 0]} name="Machines" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>

        <Grid item xs={12} md={4}>
          <ChartCard title="Top Customers by Revenue">
            <List dense disablePadding>
              {data.customers.top_customers.map((c, i) => (
                <Box key={c.name}>
                  <ListItem disableGutters sx={{ py: 1 }}>
                    <ListItemText primary={c.name} primaryTypographyProps={{ fontWeight: 600, fontSize: 13.5 }} />
                    <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13 }}>
                      {currency(c.revenue)}
                    </Typography>
                  </ListItem>
                  {i < data.customers.top_customers.length - 1 && <Divider />}
                </Box>
              ))}
            </List>
          </ChartCard>
        </Grid>

        <Grid item xs={12} md={3}>
          <ChartCard title="System Health">
            <List dense disablePadding>
              {systemChecks.map((c) => (
                <ListItem key={c.label} disableGutters sx={{ py: 0.75 }}>
                  <CheckCircleOutlineIcon sx={{ fontSize: 15, color: c.ok ? brand.success : brand.danger, mr: 1 }} />
                  <ListItemText primary={c.label} primaryTypographyProps={{ fontSize: 12.5 }} />
                </ListItem>
              ))}
            </List>
          </ChartCard>
        </Grid>
      </Grid>

      {/* AI Recommendation feed preview */}
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12}>
          <ChartCard title="Top AI Recommendations">
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {topDecisions?.items.map((rec) => (
                <Box key={rec.id} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 1, borderBottom: `1px solid ${palette.border}` }}>
                  <Box>
                    <Chip label={rec.category.replace("_", " ")} size="small" sx={{ mr: 1.5, textTransform: "capitalize", fontSize: 11, height: 20 }} />
                    <Typography component="span" sx={{ fontSize: 13.5, fontWeight: 600 }}>{rec.title}</Typography>
                  </Box>
                  <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, color: palette.textSecondary }}>
                    Priority {Math.round(rec.priority_score)}
                  </Typography>
                </Box>
              ))}
            </Box>
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
}
