import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Skeleton, Button, Menu, MenuItem, Alert } from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { apiClient } from "@/api/client";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { exportToCSV, exportToPDF, fetchAllPages } from "@/utils/export";

interface MaintenanceRecord {
  id: string;
  maintenance_type: string;
  status: string;
  scheduled_date: string | null;
  completed_date: string | null;
  ai_estimated_cost: number | null;
  ai_reasoning: string | null;
}

export function MaintenancePage() {
  const { palette } = useThemeColors();
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);

  // page_size capped at 200 to match the backend's enforced maximum
  // (settings.MAX_PAGE_SIZE) - requesting more than that returns a 422
  // validation error, which previously left this page stuck on "Loading...".
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["maintenance-list"],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: MaintenanceRecord[]; total: number }>("/maintenance", {
        params: { page: 1, page_size: 200 },
      });
      return data;
    },
  });

  const fetchAllRecords = () =>
    fetchAllPages<MaintenanceRecord>((page, pageSize) =>
      apiClient.get("/maintenance", { params: { page, page_size: pageSize } }).then((r) => r.data)
    );

  const handleExportCSV = async () => {
    const items = await fetchAllRecords();
    const rows = items.map((m) => ({
      maintenance_type: m.maintenance_type, status: m.status,
      scheduled_date: m.scheduled_date ?? "", completed_date: m.completed_date ?? "",
      ai_estimated_cost: m.ai_estimated_cost ?? "", ai_reasoning: m.ai_reasoning ?? "",
    }));
    exportToCSV(`maintenance-${new Date().toISOString().slice(0, 10)}`, rows);
    setExportAnchor(null);
  };

  const handleExportPDF = async () => {
    const items = await fetchAllRecords();
    const columns = [
      { header: "Type", key: "maintenance_type" }, { header: "Status", key: "status" },
      { header: "Scheduled", key: "scheduled_date" }, { header: "Completed", key: "completed_date" },
      { header: "Est. Cost", key: "ai_estimated_cost" },
    ];
    const rows = items.map((m) => ({
      ...m, scheduled_date: m.scheduled_date ?? "", completed_date: m.completed_date ?? "",
      ai_estimated_cost: m.ai_estimated_cost ?? "",
    }));
    exportToPDF({
      title: "Maintenance Report",
      subtitle: `${items.length} records`,
      columns: columns.map((c) => c.header),
      rows: rows.map((row) => columns.map((c) => String((row as Record<string, unknown>)[c.key] ?? ""))),
      filename: `maintenance-${new Date().toISOString().slice(0, 10)}`,
    });
    setExportAnchor(null);
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2.5 }}>
        <Box>
          <Typography variant="h5" sx={{ mb: 0.5 }}>Maintenance</Typography>
          <Typography sx={{ color: palette.textSecondary, fontSize: 14 }}>
            {isLoading ? "Loading..." : isError ? "Failed to load maintenance records" : `${data?.total ?? 0} maintenance records`}
          </Typography>
        </Box>
        <Button variant="outlined" size="small" startIcon={<DownloadOutlinedIcon />} onClick={(e) => setExportAnchor(e.currentTarget)} disabled={isLoading || isError}>
          Export
        </Button>
        <Menu anchorEl={exportAnchor} open={!!exportAnchor} onClose={() => setExportAnchor(null)}>
          <MenuItem onClick={handleExportCSV}>Export as CSV</MenuItem>
          <MenuItem onClick={handleExportPDF}>Export as PDF</MenuItem>
        </Menu>
      </Box>

      {isError && (
        <Alert severity="error" sx={{ mb: 2.5 }}>
          Could not load maintenance records: {(error as Error)?.message ?? "Unknown error"}. Please refresh the page.
        </Alert>
      )}

      <Paper sx={{ borderRadius: "10px", overflow: "hidden" }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Scheduled</TableCell>
              <TableCell>Completed</TableCell>
              <TableCell align="right">Est. Cost</TableCell>
              <TableCell>AI Reasoning</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && Array.from({ length: 6 }).map((_, i) => (
              <TableRow key={i}><TableCell colSpan={6}><Skeleton /></TableCell></TableRow>
            ))}
            {data?.items.slice(0, 50).map((m) => (
              <TableRow key={m.id} hover>
                <TableCell sx={{ textTransform: "capitalize" }}>{m.maintenance_type}</TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{m.status.replace("_", " ")}</TableCell>
                <TableCell>{m.scheduled_date ?? "\u2014"}</TableCell>
                <TableCell>{m.completed_date ?? "\u2014"}</TableCell>
                <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {m.ai_estimated_cost ? `₹${Math.round(m.ai_estimated_cost).toLocaleString("en-IN")}` : "\u2014"}
                </TableCell>
                <TableCell sx={{ fontSize: 12.5, color: palette.textSecondary, maxWidth: 320 }}>
                  {m.ai_reasoning ?? "\u2014"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
