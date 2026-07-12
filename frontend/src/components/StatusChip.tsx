import { Chip } from "@mui/material";
import { statusColorMap } from "@/theme/tokens";

export function StatusChip({ status, label }: { status: string; label?: string }) {
  const colorSet = statusColorMap[status.toLowerCase()] ?? { fg: "#5A6472", bg: "#EEF0F2" };
  return (
    <Chip
      label={label ?? status.charAt(0).toUpperCase() + status.slice(1)}
      size="small"
      sx={{
        color: colorSet.fg,
        backgroundColor: colorSet.bg,
        fontWeight: 700,
        fontSize: "0.7rem",
        letterSpacing: "0.02em",
      }}
    />
  );
}
