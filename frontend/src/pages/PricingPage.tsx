import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Box, Typography, Paper, Grid, TextField, MenuItem, Button,
  CircularProgress, Alert, Divider, Chip,
} from "@mui/material";
import RequestQuoteOutlinedIcon from "@mui/icons-material/RequestQuoteOutlined";
import { equipmentApi } from "@/api/endpoints";
import { apiClient } from "@/api/client";
import { useThemeColors } from "@/theme/ThemeModeContext";

const INDUSTRIES = [
  "oil_gas", "construction", "manufacturing", "mining", "utilities",
  "chemicals", "agriculture", "logistics", "events", "other",
];

const MONTHS = [
  { value: 1, label: "January" }, { value: 2, label: "February" }, { value: 3, label: "March" },
  { value: 4, label: "April" }, { value: 5, label: "May" }, { value: 6, label: "June" },
  { value: 7, label: "July" }, { value: 8, label: "August" }, { value: 9, label: "September" },
  { value: 10, label: "October" }, { value: 11, label: "November" }, { value: 12, label: "December" },
];

interface PriceQuoteResult {
  suggested_price: number;
  confidence_score: number;
  reasoning: string;
  model_version: string;
  model_name: string;
}

export function PricingPage() {
  const { palette, brand } = useThemeColors();

  const [equipmentId, setEquipmentId] = useState("");
  const [durationDays, setDurationDays] = useState(14);
  const [industry, setIndustry] = useState("construction");
  const [competitorPrice, setCompetitorPrice] = useState<number>(1000);
  const [inventoryCount, setInventoryCount] = useState(3);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [result, setResult] = useState<PriceQuoteResult | null>(null);

  const { data: equipmentList, isLoading: equipmentLoading } = useQuery({
    queryKey: ["pricing-equipment-list"],
    queryFn: () => equipmentApi.list({ page: 1, page_size: 200 }),
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<PriceQuoteResult>("/rentals/price-quote", null, {
        params: {
          equipment_id: equipmentId,
          duration_days: durationDays,
          customer_industry: industry,
          competitor_price: competitorPrice,
          inventory_count: inventoryCount,
          month,
        },
      });
      return data;
    },
    onSuccess: (data) => setResult(data),
  });

  const selectedEquipment = equipmentList?.items.find((e) => e.id === equipmentId);

  const currency = (n: number) =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(n);

  return (
    <Box>
      <Typography sx={{ color: palette.textSecondary, mb: 3, fontSize: 14 }}>
        Get a live AI-suggested rental price for any machine in your fleet, based on equipment health,
        competitor pricing, demand, and seasonal patterns — powered by your trained pricing model (R² 0.999).
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: "10px" }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 2 }}>Quote Parameters</Typography>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                select label="Equipment" size="small" fullWidth
                value={equipmentId} onChange={(e) => setEquipmentId(e.target.value)}
                disabled={equipmentLoading}
                helperText={equipmentLoading ? "Loading fleet..." : "Select a machine from your real fleet"}
              >
                {equipmentList?.items.map((eq) => (
                  <MenuItem key={eq.id} value={eq.id}>
                    {eq.name} — {eq.current_region} (Health: {eq.health_score?.toFixed(0) ?? "—"})
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                label="Rental Duration (days)" type="number" size="small" fullWidth
                value={durationDays} onChange={(e) => setDurationDays(Number(e.target.value))}
                inputProps={{ min: 1, max: 365 }}
              />

              <TextField
                select label="Customer Industry" size="small" fullWidth
                value={industry} onChange={(e) => setIndustry(e.target.value)}
              >
                {INDUSTRIES.map((i) => (
                  <MenuItem key={i} value={i} sx={{ textTransform: "capitalize" }}>{i.replace("_", " ")}</MenuItem>
                ))}
              </TextField>

              <TextField
                label="Competitor Daily Rate (₹)" type="number" size="small" fullWidth
                value={competitorPrice} onChange={(e) => setCompetitorPrice(Number(e.target.value))}
                helperText="What competitors currently charge for similar equipment"
              />

              <TextField
                label="Available Inventory (same type, same region)" type="number" size="small" fullWidth
                value={inventoryCount} onChange={(e) => setInventoryCount(Number(e.target.value))}
                inputProps={{ min: 0 }}
              />

              <TextField
                select label="Rental Month (seasonality)" size="small" fullWidth
                value={month} onChange={(e) => setMonth(Number(e.target.value))}
              >
                {MONTHS.map((m) => <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>)}
              </TextField>

              <Button
                variant="contained" size="large"
                startIcon={mutation.isPending ? <CircularProgress size={18} sx={{ color: "#fff" }} /> : <RequestQuoteOutlinedIcon />}
                disabled={!equipmentId || mutation.isPending}
                onClick={() => mutation.mutate()}
                sx={{ mt: 1, py: 1.2 }}
              >
                {mutation.isPending ? "Calculating..." : "Get AI Price Quote"}
              </Button>

              {mutation.isError && (
                <Alert severity="error">
                  Could not generate a quote. Please check the selected equipment and try again.
                </Alert>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: "10px", height: "100%" }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 2 }}>AI Price Recommendation</Typography>

            {!result && !mutation.isPending && (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <RequestQuoteOutlinedIcon sx={{ fontSize: 40, color: palette.border, mb: 1 }} />
                <Typography sx={{ color: palette.textSecondary, fontSize: 13 }}>
                  Fill in the parameters and click "Get AI Price Quote" to see a live recommendation.
                </Typography>
              </Box>
            )}

            {result && (
              <Box>
                {selectedEquipment && (
                  <Chip label={selectedEquipment.name} size="small" sx={{ mb: 2, fontWeight: 600 }} />
                )}

                <Typography sx={{ fontSize: 12, color: palette.textSecondary, fontWeight: 700, textTransform: "uppercase" }}>
                  Suggested Daily Rate
                </Typography>
                <Typography sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 40, fontWeight: 700, color: brand.primary, my: 0.5 }}>
                  {currency(result.suggested_price)}
                </Typography>

                <Box sx={{ display: "flex", gap: 3, my: 2 }}>
                  <Box>
                    <Typography sx={{ fontSize: 11, color: palette.textSecondary, fontWeight: 700 }}>CONFIDENCE</Typography>
                    <Typography sx={{ fontWeight: 700, fontSize: 18 }}>{Math.round(result.confidence_score * 100)}%</Typography>
                  </Box>
                  <Box>
                    <Typography sx={{ fontSize: 11, color: palette.textSecondary, fontWeight: 700 }}>MODEL</Typography>
                    <Typography sx={{ fontWeight: 700, fontSize: 13, mt: 0.5 }}>{result.model_version}</Typography>
                  </Box>
                </Box>

                <Divider sx={{ my: 2 }} />

                <Typography sx={{ fontSize: 12, color: palette.textSecondary, fontWeight: 700, textTransform: "uppercase", mb: 1 }}>
                  Business Reasoning
                </Typography>
                <Typography sx={{ fontSize: 13, lineHeight: 1.7 }}>{result.reasoning}</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
