import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Box, Typography, Paper, Chip, MenuItem, TextField, Skeleton, LinearProgress,
  Button, Tabs, Tab, Snackbar, Alert,
} from "@mui/material";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import { decisionsApi } from "@/api/endpoints";
import { useThemeColors } from "@/theme/ThemeModeContext";

const CATEGORY_LABELS: Record<string, string> = {
  maintenance: "Maintenance",
  fleet_replacement: "Fleet Replacement",
  inventory_relocation: "Inventory Relocation",
  customer_retention: "Customer Retention",
  pricing: "Pricing",
  risk_mitigation: "Risk Mitigation",
};

const currency = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

function priorityLabel(score: number): { label: string; color: string } {
  if (score >= 70) return { label: "High", color: "#C43D3D" };
  if (score >= 40) return { label: "Medium", color: "#C7861A" };
  return { label: "Low", color: "#1E8E5A" };
}

export function DecisionsPage() {
  const { palette, brand } = useThemeColors();
  const queryClient = useQueryClient();
  const [category, setCategory] = useState("");
  const [statusTab, setStatusTab] = useState<"pending" | "accepted" | "rejected">("pending");
  const [toast, setToast] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["decisions", category, statusTab],
    queryFn: () => decisionsApi.list({ page: 1, page_size: 50, category: category || undefined, status: statusTab }),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => decisionsApi.updateStatus(id, status),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["decisions"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-count"] });
      setToast(variables.status === "accepted" ? "Recommendation approved." : "Recommendation rejected.");
    },
  });

  return (
    <Box>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        AI-generated business recommendations from your fleet's health, pricing, and demand models — ranked by priority.
      </Typography>

      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2, mb: 1 }}>
        <Tabs value={statusTab} onChange={(_, v) => setStatusTab(v)} sx={{ minHeight: 36 }}>
          <Tab value="pending" label="Pending" sx={{ minHeight: 36, fontSize: 13 }} />
          <Tab value="accepted" label="Approved" sx={{ minHeight: 36, fontSize: 13 }} />
          <Tab value="rejected" label="Rejected" sx={{ minHeight: 36, fontSize: 13 }} />
        </Tabs>

        <TextField
          size="small" select label="Category" value={category}
          onChange={(e) => setCategory(e.target.value)}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">All categories</MenuItem>
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => <MenuItem key={k} value={k}>{v}</MenuItem>)}
        </TextField>
      </Box>

      <Typography sx={{ fontSize: 13, color: palette.textSecondary, mb: 2.5 }}>
        {data ? `${data.total} recommendations` : "Loading..."}
      </Typography>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {isLoading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rounded" height={110} />)}

        {data?.items.length === 0 && (
          <Paper sx={{ p: 5, borderRadius: "10px", textAlign: "center" }}>
            <Typography sx={{ color: palette.textSecondary, fontSize: 14 }}>
              No {statusTab} recommendations{category ? ` in ${CATEGORY_LABELS[category]}` : ""}.
            </Typography>
          </Paper>
        )}

        {data?.items.map((rec) => {
          const p = priorityLabel(rec.priority_score);
          return (
            <Paper key={rec.id} sx={{ p: 2.5, borderRadius: "10px" }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.75, flexWrap: "wrap" }}>
                    <Chip
                      label={CATEGORY_LABELS[rec.category] ?? rec.category}
                      size="small"
                      sx={{ bgcolor: `${brand.primary}1A`, color: brand.primary, fontWeight: 700, fontSize: "0.7rem" }}
                    />
                    <Chip
                      label={`${p.label} Priority`}
                      size="small"
                      sx={{ bgcolor: `${p.color}1A`, color: p.color, fontWeight: 700, fontSize: "0.7rem" }}
                    />
                    {rec.estimated_impact_value != null && (
                      <Typography sx={{ fontSize: 12, color: palette.textSecondary, fontFamily: "'JetBrains Mono', monospace" }}>
                        Est. impact: {currency(rec.estimated_impact_value)}
                        {rec.estimated_impact_metric ? ` (${rec.estimated_impact_metric.replace("_", " ")})` : ""}
                      </Typography>
                    )}
                  </Box>
                  <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{rec.title}</Typography>
                  <Typography sx={{ fontSize: 13.5, color: palette.textSecondary, mt: 0.25 }}>{rec.summary}</Typography>
                  <Typography sx={{ fontSize: 12.5, color: palette.textSecondary, mt: 1, lineHeight: 1.6 }}>
                    {rec.detailed_reasoning}
                  </Typography>
                </Box>

                <Box sx={{ minWidth: 100, textAlign: "right", flexShrink: 0 }}>
                  <Typography sx={{ fontSize: 11, color: palette.textSecondary, fontWeight: 700 }}>CONFIDENCE</Typography>
                  <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 18 }}>
                    {Math.round(rec.confidence_score * 100)}%
                  </Typography>

                  {statusTab === "pending" && (
                    <Box sx={{ display: "flex", gap: 0.75, mt: 1.5, justifyContent: "flex-end" }}>
                      <Button
                        size="small" variant="contained" color="success"
                        startIcon={<CheckOutlinedIcon fontSize="small" />}
                        onClick={() => mutation.mutate({ id: rec.id, status: "accepted" })}
                        disabled={mutation.isPending}
                        sx={{ minWidth: 0, px: 1.25 }}
                      >
                        Approve
                      </Button>
                      <Button
                        size="small" variant="outlined" color="error"
                        startIcon={<CloseOutlinedIcon fontSize="small" />}
                        onClick={() => mutation.mutate({ id: rec.id, status: "rejected" })}
                        disabled={mutation.isPending}
                        sx={{ minWidth: 0, px: 1.25 }}
                      >
                        Reject
                      </Button>
                    </Box>
                  )}
                </Box>
              </Box>
              <LinearProgress
                variant="determinate" value={rec.priority_score}
                sx={{ mt: 1.5, height: 4, borderRadius: 2, bgcolor: palette.border, "& .MuiLinearProgress-bar": { bgcolor: p.color } }}
              />
            </Paper>
          );
        })}
      </Box>

      <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast(null)}>
        <Alert severity="success" onClose={() => setToast(null)}>{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
