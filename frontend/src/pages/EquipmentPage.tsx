import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  TextField, MenuItem, Chip, Skeleton, TablePagination,
} from "@mui/material";
import { equipmentApi } from "@/api/endpoints";
import { colors } from "@/theme/tokens";
import { StatusChip } from "@/components/StatusChip";

export function EquipmentPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [search, setSearch] = useState("");

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

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Equipment</Typography>
      <Typography sx={{ color: colors.textSecondary, mb: 3, fontSize: 14 }}>
        {data ? `${data.total} machines in your fleet` : "Loading fleet..."}
      </Typography>

      <Box sx={{ display: "flex", gap: 1.5, mb: 2.5, flexWrap: "wrap" }}>
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

      <Paper sx={{ borderRadius: "12px", overflow: "hidden" }}>
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
                  <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: colors.textSecondary }}>
                    {eq.asset_tag}
                  </Typography>
                </TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{eq.equipment_type.replace("_", " ")}</TableCell>
                <TableCell>{eq.current_region}</TableCell>
                <TableCell sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {eq.health_score?.toFixed(1) ?? "—"}
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
