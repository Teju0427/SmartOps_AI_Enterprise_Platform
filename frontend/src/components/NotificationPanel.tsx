import { Box, Menu, Typography, List, ListItem, ListItemText, Divider, Chip } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { decisionsApi } from "@/api/endpoints";
import { useThemeColors } from "@/theme/ThemeModeContext";

interface NotificationPanelProps {
  anchorEl: HTMLElement | null;
  onClose: () => void;
}

/**
 * Surfaces the highest-priority pending AI recommendations as
 * notifications - reuses the existing /decisions endpoint rather than
 * inventing a separate notifications API, since a pending high-priority
 * recommendation IS the notification that matters in this product.
 */
export function NotificationPanel({ anchorEl, onClose }: NotificationPanelProps) {
  const { palette, statusColor } = useThemeColors();

  const { data } = useQuery({
    queryKey: ["notifications-preview"],
    queryFn: () => decisionsApi.list({ page: 1, page_size: 6 }),
    enabled: !!anchorEl,
  });

  return (
    <Menu
      anchorEl={anchorEl}
      open={!!anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      slotProps={{ paper: { sx: { width: 380, maxHeight: 480 } } }}
    >
      <Box sx={{ px: 2, py: 1.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography sx={{ fontWeight: 700, fontSize: 14 }}>Notifications</Typography>
        {data && <Chip label={`${data.total} pending`} size="small" sx={{ fontSize: 11, height: 20 }} />}
      </Box>
      <Divider />
      <List dense disablePadding>
        {data?.items.length === 0 && (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography sx={{ fontSize: 13, color: palette.textSecondary }}>No pending recommendations.</Typography>
          </Box>
        )}
        {data?.items.map((item) => {
          const isHigh = item.priority_score >= 70;
          const sc = statusColor(isHigh ? "critical" : "warning");
          return (
            <ListItem key={item.id} sx={{ py: 1.25, px: 2, alignItems: "flex-start", gap: 1 }}>
              <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: sc.fg, mt: 0.9, flexShrink: 0 }} />
              <ListItemText
                primary={item.title}
                secondary={item.summary}
                primaryTypographyProps={{ fontWeight: 600, fontSize: 13 }}
                secondaryTypographyProps={{ fontSize: 12, sx: { color: palette.textSecondary } }}
              />
            </ListItem>
          );
        })}
      </List>
    </Menu>
  );
}
