import { useQuery } from "@tanstack/react-query";
import { Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Skeleton } from "@mui/material";
import { apiClient } from "@/api/client";
import { colors } from "@/theme/tokens";

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
  const { data, isLoading } = useQuery({
    queryKey: ["maintenance-list"],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: MaintenanceRecord[]; total: number }>("/maintenance", {
        params: { page: 1, page_size: 30 },
      });
      return data;
    },
  });

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Maintenance</Typography>
      <Typography sx={{ color: colors.textSecondary, mb: 3, fontSize: 14 }}>
        {data ? `${data.total} maintenance records` : "Loading..."}
      </Typography>

      <Paper sx={{ borderRadius: "12px", overflow: "hidden" }}>
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
            {data?.items.map((m) => (
              <TableRow key={m.id} hover>
                <TableCell sx={{ textTransform: "capitalize" }}>{m.maintenance_type}</TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{m.status.replace("_", " ")}</TableCell>
                <TableCell>{m.scheduled_date ?? "—"}</TableCell>
                <TableCell>{m.completed_date ?? "—"}</TableCell>
                <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {m.ai_estimated_cost ? `₹${Math.round(m.ai_estimated_cost).toLocaleString("en-IN")}` : "—"}
                </TableCell>
                <TableCell sx={{ fontSize: 12.5, color: colors.textSecondary, maxWidth: 320 }}>
                  {m.ai_reasoning ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
