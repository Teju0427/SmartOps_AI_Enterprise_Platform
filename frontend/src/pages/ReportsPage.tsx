import { useState } from "react";
import { Box, Typography, Paper, Button, Grid, CircularProgress } from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { apiClient } from "@/api/client";
import { equipmentApi, decisionsApi } from "@/api/endpoints";
import { exportToCSV, exportToPDF, fetchAllPages } from "@/utils/export";

interface ReportDef {
  key: string;
  title: string;
  desc: string;
  fetchRows: () => Promise<Record<string, unknown>[]>;
  columns: { header: string; dataKey: string }[];
}

// All fetchRows implementations use fetchAllPages (200-record pages,
// looped) instead of a single oversized page_size - the backend rejects
// any page_size above 200 with a 422 validation error, which previously
// caused every export on this page to silently fail.
const REPORTS: ReportDef[] = [
  {
    key: "equipment",
    title: "Equipment Report",
    desc: "Full fleet health, utilization, and status across all machines.",
    fetchRows: async () => {
      const items = await fetchAllPages((page, page_size) => equipmentApi.list({ page, page_size }));
      return items.map((e) => ({
        machine_id: e.machine_id, name: e.name, type: e.equipment_type,
        region: e.current_region, health_score: e.health_score, status: e.status,
        availability: e.availability, daily_rate: e.base_daily_rate,
      }));
    },
    columns: [
      { header: "Machine ID", dataKey: "machine_id" }, { header: "Name", dataKey: "name" },
      { header: "Type", dataKey: "type" }, { header: "Region", dataKey: "region" },
      { header: "Health", dataKey: "health_score" }, { header: "Status", dataKey: "status" },
      { header: "Daily Rate", dataKey: "daily_rate" },
    ],
  },
  {
    key: "customers",
    title: "Customer Analytics",
    desc: "Revenue, industry breakdown, and payment risk per customer.",
    fetchRows: async () => {
      const items = await fetchAllPages<Record<string, unknown>>((page, page_size) =>
        apiClient.get("/customers", { params: { page, page_size } }).then((r) => r.data)
      );
      return items.map((c) => ({
        company_name: c.company_name, industry: c.industry, region: c.region,
        total_rentals: c.total_rentals, total_revenue: c.total_revenue,
      }));
    },
    columns: [
      { header: "Company", dataKey: "company_name" }, { header: "Industry", dataKey: "industry" },
      { header: "Region", dataKey: "region" }, { header: "Rentals", dataKey: "total_rentals" },
      { header: "Revenue", dataKey: "total_revenue" },
    ],
  },
  {
    key: "maintenance",
    title: "Maintenance Report",
    desc: "Completed and scheduled maintenance with AI cost estimates.",
    fetchRows: async () => {
      const items = await fetchAllPages<Record<string, unknown>>((page, page_size) =>
        apiClient.get("/maintenance", { params: { page, page_size } }).then((r) => r.data)
      );
      return items.map((m) => ({
        type: m.maintenance_type, status: m.status,
        scheduled_date: m.scheduled_date ?? "", estimated_cost: m.ai_estimated_cost ?? "",
      }));
    },
    columns: [
      { header: "Type", dataKey: "type" }, { header: "Status", dataKey: "status" },
      { header: "Scheduled", dataKey: "scheduled_date" }, { header: "Est. Cost", dataKey: "estimated_cost" },
    ],
  },
  {
    key: "decisions",
    title: "AI Decisions Report",
    desc: "All AI-generated recommendations with priority and reasoning.",
    fetchRows: async () => {
      const items = await fetchAllPages((page, page_size) => decisionsApi.list({ page, page_size }));
      return items.map((d) => ({
        category: d.category, title: d.title, priority: d.priority_score,
        confidence: d.confidence_score, status: d.status,
      }));
    },
    columns: [
      { header: "Category", dataKey: "category" }, { header: "Title", dataKey: "title" },
      { header: "Priority", dataKey: "priority" }, { header: "Confidence", dataKey: "confidence" },
      { header: "Status", dataKey: "status" },
    ],
  },
];

export function ReportsPage() {
  const { palette } = useThemeColors();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  const handleExport = async (report: ReportDef, format: "csv" | "pdf") => {
    setLoadingKey(report.key);
    setErrorKey(null);
    try {
      const rows = await report.fetchRows();
      const filename = `${report.key}-report-${new Date().toISOString().slice(0, 10)}`;
      if (format === "csv") {
        exportToCSV(filename, rows);
      } else {
        exportToPDF({
          title: report.title,
          subtitle: `${rows.length} records`,
          columns: report.columns.map((c) => c.header),
          rows: rows.map((row) => report.columns.map((c) => String(row[c.dataKey] ?? ""))),
          filename,
        });
      }
    } catch (err) {
      console.error("Export failed:", err);
      setErrorKey(report.key);
    } finally {
      setLoadingKey(null);
    }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Reports</Typography>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        Export real operational data from across the platform as CSV or PDF.
      </Typography>

      <Grid container spacing={2.5}>
        {REPORTS.map((r) => (
          <Grid item xs={12} sm={6} md={4} key={r.key}>
            <Paper sx={{ p: 2.5, borderRadius: "10px", height: "100%", display: "flex", flexDirection: "column" }}>
              <Typography sx={{ fontWeight: 700, fontSize: 15, mb: 0.5 }}>{r.title}</Typography>
              <Typography sx={{ fontSize: 13, color: palette.textSecondary, flexGrow: 1, mb: 2 }}>{r.desc}</Typography>
              {errorKey === r.key && (
                <Typography sx={{ fontSize: 12, color: "error.main", mb: 1 }}>
                  Export failed. Check your connection and try again.
                </Typography>
              )}
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  size="small" variant="outlined"
                  startIcon={loadingKey === r.key ? <CircularProgress size={14} /> : <DownloadOutlinedIcon />}
                  disabled={loadingKey === r.key}
                  onClick={() => handleExport(r, "csv")}
                >
                  CSV
                </Button>
                <Button
                  size="small" variant="outlined"
                  startIcon={loadingKey === r.key ? <CircularProgress size={14} /> : <DownloadOutlinedIcon />}
                  disabled={loadingKey === r.key}
                  onClick={() => handleExport(r, "pdf")}
                >
                  PDF
                </Button>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
