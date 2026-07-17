import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  TextField, MenuItem, Chip, Skeleton, TablePagination, Button, Menu, MenuItem as MItem,
} from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { equipmentApi } from "@/api/endpoints";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { StatusChip } from "@/components/StatusChip";
import { exportToCSV, exportToPDF, fetchAllPages } from "@/utils/export";

export function EquipmentPage() {
  const { palette } = useThemeColors();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [search, setSearch] = useState("");
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);

  const { data: regions } = useQuery({ queryKey: ["equipment-regions"], queryFn: equipmentApi.getRegions });

  const { data, isLoading } = useQuery({
    queryKey: ["equipment-list", page, pageSize, statusFilter, regionFilter, search],
    queryFn: () =>
      equipmentApi.list({
        page: page + 1,
        page_size: pageSize,
        status: statusFilter || undefined,
        region: regionFilter || undefined,
        search: search || undefined,
      }),
  });

  // Export pulls the FULL filtered result set across multiple 200-record
  // pages (the backend's enforced max page_size) directly from the real
  // API, so downloads always reflect actual fleet data.
  const fetchAllFiltered = () =>
    fetchAllPages((page, pageSize) =>
      equipmentApi.list({
        page, page_size: pageSize,
        status: statusFilter || undefined, region: regionFilter || undefined, search: search || undefined,
      })
    ).then((items) =>
      items.map((eq) => ({
        machine_id: eq.machine_id, asset_tag: eq.asset_tag, name: eq.name,
        equipment_type: eq.equipment_type, manufacturer: eq.manufacturer, model_number: eq.model_number,
        health_score: eq.health_score, status: eq.status, availability: eq.availability,
        current_region: eq.current_region, base_daily_rate: eq.base_daily_rate,
        total_operating_hours: eq.total_operating_hours,
      }))
    );

  const handleExportCSV = async () => {
    const rows = await fetchAllFiltered();
    exportToCSV(`equipment-fleet-${new Date().toISOString().slice(0, 10)}`, rows);
    setExportAnchor(null);
  };

  const handleExportPDF = async () => {
    const rows = await fetchAllFiltered();
    const columns = [
      { header: "Machine", key: "name" }, { header: "Asset Tag", key: "asset_tag" },
      { header: "Type", key: "equipment_type" }, { header: "Region", key: "current_region" },
      { header: "Health", key: "health_score" }, { header: "Status", key: "status" },
      { header: "Availability", key: "availability" }, { header: "Daily Rate", key: "base_daily_rate" },
    ];
    exportToPDF({
      title: "Equipment Fleet Report",
      subtitle: `${rows.length} machines`,
      columns: columns.map((c) => c.header),
      rows: rows.map((row) => columns.map((c) => String((row as Record<string, unknown>)[c.key] ?? ""))),
      filename: `equipment-fleet-${new Date().toISOString().slice(0, 10)}`,
    });
    setExportAnchor(null);
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 0.5 }}>
        <Box>
          <Typography variant="h5" sx={{ mb: 0.5 }}>Equipment</Typography>
          <Typography sx={{ color: palette.textSecondary, fontSize: 14 }}>
            {data ? `${data.total} machines in your fleet` : "Loading fleet..."}
          </Typography>
        </Box>
        <Button
          variant="outlined" size="small" startIcon={<DownloadOutlinedIcon />}
          onClick={(e) => setExportAnchor(e.currentTarget)}
        >
          Export
        </Button>
        <Menu anchorEl={exportAnchor} open={!!exportAnchor} onClose={() => setExportAnchor(null)}>
          <MItem onClick={handleExportCSV}>Export as CSV</MItem>
          <MItem onClick={handleExportPDF}>Export as PDF</MItem>
        </Menu>
      </Box>

      <Box sx={{ display: "flex", gap: 1.5, mb: 2.5, mt: 2.5, flexWrap: "wrap" }}>
        <TextField
          size="small" placeholder="Search by name, tag, or ID" value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          sx={{ minWidth: 240 }}
        />
        <TextField
          size="small" select label="Status" value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All statuses</MenuItem>
          <MenuItem value="healthy">Healthy</MenuItem>
          <MenuItem value="warning">Warning</MenuItem>
          <MenuItem value="critical">Critical</MenuItem>
        </TextField>
        <TextField
          size="small" select label="Region" value={regionFilter}
          onChange={(e) => { setRegionFilter(e.target.value); setPage(0); }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All regions</MenuItem>
          {regions?.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
        </TextField>
      </Box>

      <Paper sx={{ borderRadius: "10px", overflow: "hidden" }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Machine</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Region</TableCell>
              <TableCell>Health</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Availability</TableCell>
              <TableCell align="right">Daily Rate</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading &&
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}><Skeleton /></TableCell>
                </TableRow>
              ))}
            {data?.items.map((eq) => (
              <TableRow key={eq.id} hover sx={{ cursor: "pointer" }}>
                <TableCell>
                  <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{eq.name}</Typography>
                  <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: palette.textSecondary }}>
                    {eq.asset_tag}
                  </Typography>
                </TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{eq.equipment_type.replace("_", " ")}</TableCell>
                <TableCell>{eq.current_region}</TableCell>
                <TableCell sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {eq.health_score?.toFixed(1) ?? "\u2014"}
                </TableCell>
                <TableCell><StatusChip status={eq.status} /></TableCell>
                <TableCell>
                  <Chip label={eq.availability.replace("_", " ")} size="small" variant="outlined" sx={{ textTransform: "capitalize" }} />
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  ₹{eq.base_daily_rate.toLocaleString("en-IN")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {data && (
          <TablePagination
            component="div"
            count={data.total}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => { setPageSize(parseInt(e.target.value, 10)); setPage(0); }}
            rowsPerPageOptions={[10, 20, 50]}
          />
        )}
      </Paper>
    </Box>
  );
}
