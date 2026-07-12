import { useQuery } from "@tanstack/react-query";
import { Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Skeleton, Chip } from "@mui/material";
import { apiClient } from "@/api/client";
import { colors } from "@/theme/tokens";
import { StatusChip } from "@/components/StatusChip";

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
  const { data, isLoading } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: Customer[]; total: number }>("/customers", {
        params: { page: 1, page_size: 30 },
      });
      return data;
    },
  });

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>Customers</Typography>
      <Typography sx={{ color: colors.textSecondary, mb: 3, fontSize: 14 }}>
        {data ? `${data.total} customer accounts` : "Loading..."}
      </Typography>

      <Paper sx={{ borderRadius: "12px", overflow: "hidden" }}>
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
            {data?.items.map((c) => (
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
