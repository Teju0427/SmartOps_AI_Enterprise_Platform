import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Skeleton, Chip, Button, Menu, MenuItem, Alert } from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { apiClient } from "@/api/client";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { StatusChip } from "@/components/StatusChip";
import { exportToCSV, exportToPDF, fetchAllPages } from "@/utils/export";

interface Customer {
  id: string;
  company_name: string;
  industry: string;
  region: string;
  total_rentals: number;
  total_revenue: number;
  late_payment_risk: string | null;
}

export function CustomersPage() {
  const { palette } = useThemeColors();
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);

  // page_size capped at 200 to match the backend's enforced maximum -
  // requesting 500 (as before) returned a 422 and left this page stuck
  // on "Loading..." indefinitely since the error state was never checked.
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: Customer[]; total: number }>("/customers", {
        params: { page: 1, page_size: 200 },
      });
      return data;
    },
  });

  const fetchAllCustomers = () =>
    fetchAllPages<Customer>((page, pageSize) =>
      apiClient.get("/customers", { params: { page, page_size: pageSize } }).then((r) => r.data)
    );

  const handleExportCSV = async () => {
    const items = await fetchAllCustomers();
    const rows = items.map((c) => ({
      company_name: c.company_name, industry: c.industry, region: c.region,
      total_rentals: c.total_rentals, total_revenue: c.total_revenue,
      late_payment_risk: c.late_payment_risk ?? "unrated",
    }));
    exportToCSV(`customers-${new Date().toISOString().slice(0, 10)}`, rows);
    setExportAnchor(null);
  };

  const handleExportPDF = async () => {
    const items = await fetchAllCustomers();
    const columns = [
      { header: "Company", key: "company_name" }, { header: "Industry", key: "industry" },
      { header: "Region", key: "region" }, { header: "Rentals", key: "total_rentals" },
      { header: "Total Revenue", key: "total_revenue" }, { header: "Payment Risk", key: "late_payment_risk" },
    ];
    const rows = items.map((c) => ({ ...c, late_payment_risk: c.late_payment_risk ?? "unrated" }));
    exportToPDF({
      title: "Customer Report",
      subtitle: `${items.length} customer accounts`,
      columns: columns.map((c) => c.header),
      rows: rows.map((row) => columns.map((c) => String((row as Record<string, unknown>)[c.key] ?? ""))),
      filename: `customers-${new Date().toISOString().slice(0, 10)}`,
    });
    setExportAnchor(null);
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2.5 }}>
        <Box>
          <Typography variant="h5" sx={{ mb: 0.5 }}>Customers</Typography>
          <Typography sx={{ color: palette.textSecondary, fontSize: 14 }}>
            {isLoading ? "Loading..." : isError ? "Failed to load customers" : `${data?.total ?? 0} customer accounts`}
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
          Could not load customers: {(error as Error)?.message ?? "Unknown error"}. Please refresh the page.
        </Alert>
      )}

      <Paper sx={{ borderRadius: "10px", overflow: "hidden" }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Company</TableCell>
              <TableCell>Industry</TableCell>
              <TableCell>Region</TableCell>
              <TableCell align="right">Rentals</TableCell>
              <TableCell align="right">Total Revenue</TableCell>
              <TableCell>Payment Risk</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && Array.from({ length: 6 }).map((_, i) => (
              <TableRow key={i}><TableCell colSpan={6}><Skeleton /></TableCell></TableRow>
            ))}
            {data?.items.slice(0, 50).map((c) => (
              <TableRow key={c.id} hover>
                <TableCell sx={{ fontWeight: 600 }}>{c.company_name}</TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{c.industry.replace("_", " ")}</TableCell>
                <TableCell>{c.region}</TableCell>
                <TableCell align="right">{c.total_rentals}</TableCell>
                <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  ₹{Math.round(c.total_revenue).toLocaleString("en-IN")}
                </TableCell>
                <TableCell>
                  {c.late_payment_risk ? <StatusChip status={c.late_payment_risk} /> : <Chip label="Unrated" size="small" variant="outlined" />}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
