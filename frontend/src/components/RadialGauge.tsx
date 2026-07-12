import { Box, Typography } from "@mui/material";
import { colors, statusColorMap } from "@/theme/tokens";

interface RadialGaugeProps {
  value: number; // 0-100
  status: "healthy" | "warning" | "critical";
  size?: number;
  label?: string;
}

/**
 * Signature visual element: a radial gauge for equipment health scores.
 * Chosen deliberately over a plain number or bar - this platform's core
 * job is turning raw sensor telemetry into an at-a-glance health read,
 * and an instrument-style gauge (evoking the dials on the equipment
 * itself) makes that legible in a way a flat percentage can't.
 */
export function RadialGauge({ value, status, size = 96, label }: RadialGaugeProps) {
  const strokeWidth = size * 0.09;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value / 100);
  const color = statusColorMap[status]?.fg ?? colors.textSecondary;

  return (
    <Box sx={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 0.5 }}>
      <Box sx={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.border}
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography
            sx={{
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              fontSize: size * 0.24,
              color: colors.textPrimary,
              lineHeight: 1,
            }}
          >
            {Math.round(value)}
          </Typography>
          <Typography sx={{ fontSize: size * 0.09, color: colors.textSecondary, fontWeight: 600 }}>
            / 100
          </Typography>
        </Box>
      </Box>
      {label && (
        <Typography sx={{ fontSize: 12, color: colors.textSecondary, fontWeight: 600 }}>{label}</Typography>
      )}
    </Box>
  );
}
