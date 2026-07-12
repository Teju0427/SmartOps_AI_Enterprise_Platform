import { useState } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Typography,
  AppBar, Toolbar, IconButton, Avatar, Menu, MenuItem, Divider, InputBase,
  Badge, Switch, Breadcrumbs, Link as MuiLink, Tooltip,
} from "@mui/material";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import PrecisionManufacturingOutlinedIcon from "@mui/icons-material/PrecisionManufacturingOutlined";
import BuildOutlinedIcon from "@mui/icons-material/BuildOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import { useThemeColors } from "@/theme/ThemeModeContext";
import { useAuth } from "@/contexts/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { decisionsApi } from "@/api/endpoints";
import { NotificationPanel } from "@/components/NotificationPanel";

const DRAWER_WIDTH = 252;

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: <DashboardOutlinedIcon fontSize="small" /> },
  { label: "Equipment", path: "/equipment", icon: <PrecisionManufacturingOutlinedIcon fontSize="small" /> },
  { label: "AI Decisions", path: "/decisions", icon: <AutoAwesomeOutlinedIcon fontSize="small" /> },
  { label: "Maintenance", path: "/maintenance", icon: <BuildOutlinedIcon fontSize="small" /> },
  { label: "Customers", path: "/customers", icon: <GroupsOutlinedIcon fontSize="small" /> },
  { label: "Forecasts", path: "/forecasts", icon: <InsightsOutlinedIcon fontSize="small" /> },
  { label: "Reports", path: "/reports", icon: <DescriptionOutlinedIcon fontSize="small" /> },
  { label: "Settings", path: "/settings", icon: <SettingsOutlinedIcon fontSize="small" /> },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/equipment": "Equipment",
  "/decisions": "AI Decisions",
  "/maintenance": "Maintenance",
  "/customers": "Customers",
  "/forecasts": "Forecasts",
  "/reports": "Reports",
  "/settings": "Settings",
};

export function AppLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { palette, brand, mode, toggleMode } = useThemeColors();
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [notifAnchor, setNotifAnchor] = useState<null | HTMLElement>(null);

  const { data: pendingDecisions } = useQuery({
    queryKey: ["notifications-count"],
    queryFn: () => decisionsApi.list({ page: 1, page_size: 1 }),
    refetchInterval: 60_000,
  });

  const currentTitle = PAGE_TITLES[location.pathname] ?? "RentalIQ";
  const today = new Date().toLocaleDateString("en-IN", { weekday: "short", year: "numeric", month: "short", day: "numeric" });

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: palette.bgDefault }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH, boxSizing: "border-box", bgcolor: palette.bgSidebar, borderRight: "none" },
        }}
      >
        <Box sx={{ px: 3, py: 3, display: "flex", alignItems: "center", gap: 1.25 }}>
          <Box
            sx={{
              width: 32, height: 32, borderRadius: "7px", bgcolor: brand.primary,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <InsightsOutlinedIcon sx={{ color: "#FFFFFF", fontSize: 18 }} />
          </Box>
          <Box>
            <Typography sx={{ color: palette.textOnSidebar, fontWeight: 700, fontSize: 16, lineHeight: 1.1 }}>
              RentalIQ
            </Typography>
            <Typography sx={{ color: palette.textOnSidebarMuted, fontSize: 10.5 }}>
              Enterprise AI Platform
            </Typography>
          </Box>
        </Box>

        <List sx={{ px: 1.5, mt: 1, flexGrow: 1 }}>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
            return (
              <ListItemButton
                key={item.path}
                component={NavLink}
                to={item.path}
                sx={{
                  borderRadius: "6px",
                  mb: 0.25,
                  py: 0.9,
                  color: active ? palette.textOnSidebar : palette.textOnSidebarMuted,
                  bgcolor: active ? palette.bgSidebarActive : "transparent",
                  borderLeft: active ? `3px solid ${brand.primary}` : "3px solid transparent",
                  transition: "background-color 0.15s ease, color 0.15s ease",
                  "&:hover": { bgcolor: palette.bgSidebarActive },
                }}
              >
                <ListItemIcon sx={{ color: active ? "#5B9BD5" : palette.textOnSidebarMuted, minWidth: 34 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 13.5, fontWeight: active ? 700 : 500 }} />
              </ListItemButton>
            );
          })}
        </List>

        <Divider sx={{ borderColor: palette.border, opacity: 0.15, mx: 2 }} />
        <ListItemButton onClick={logout} sx={{ mx: 1.5, my: 1.5, borderRadius: "6px", color: palette.textOnSidebarMuted }}>
          <ListItemIcon sx={{ color: palette.textOnSidebarMuted, minWidth: 34 }}>
            <LogoutOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Log out" primaryTypographyProps={{ fontSize: 13.5, fontWeight: 500 }} />
        </ListItemButton>
      </Drawer>

      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
        <AppBar
          position="sticky"
          elevation={0}
          sx={{ bgcolor: palette.bgPaper, color: palette.textPrimary, borderBottom: `1px solid ${palette.border}` }}
        >
          <Toolbar sx={{ gap: 2, minHeight: "64px !important" }}>
            <Box sx={{ flexGrow: 1 }}>
              <Breadcrumbs sx={{ fontSize: 12 }}>
                <MuiLink underline="hover" sx={{ fontSize: 12, color: palette.textSecondary }} component={NavLink} to="/">
                  RentalIQ
                </MuiLink>
                <Typography sx={{ fontSize: 12, color: palette.textPrimary, fontWeight: 600 }}>{currentTitle}</Typography>
              </Breadcrumbs>
              <Typography sx={{ fontWeight: 700, fontSize: 17, mt: 0.25 }}>{currentTitle}</Typography>
            </Box>

            <Box
              sx={{
                display: { xs: "none", md: "flex" }, alignItems: "center", gap: 1,
                bgcolor: palette.bgDefault, borderRadius: "6px", px: 1.5, py: 0.6, width: 260,
                border: `1px solid ${palette.border}`,
              }}
            >
              <SearchOutlinedIcon sx={{ fontSize: 18, color: palette.textSecondary }} />
              <InputBase placeholder="Search equipment, customers..." sx={{ fontSize: 13.5, flex: 1 }} />
            </Box>

            <Typography sx={{ display: { xs: "none", lg: "block" }, fontSize: 12.5, color: palette.textSecondary, whiteSpace: "nowrap" }}>
              {today}
            </Typography>

            <Tooltip title={mode === "light" ? "Switch to dark mode" : "Switch to light mode"}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <LightModeOutlinedIcon sx={{ fontSize: 17, color: mode === "light" ? brand.warning : palette.textSecondary }} />
                <Switch size="small" checked={mode === "dark"} onChange={toggleMode} />
                <DarkModeOutlinedIcon sx={{ fontSize: 17, color: mode === "dark" ? brand.primary : palette.textSecondary }} />
              </Box>
            </Tooltip>

            <IconButton onClick={(e) => setNotifAnchor(e.currentTarget)}>
              <Badge badgeContent={pendingDecisions?.total ?? 0} color="error" max={99}>
                <NotificationsNoneOutlinedIcon />
              </Badge>
            </IconButton>
            <NotificationPanel anchorEl={notifAnchor} onClose={() => setNotifAnchor(null)} />

            <IconButton onClick={(e) => setUserMenuAnchor(e.currentTarget)}>
              <Avatar sx={{ width: 34, height: 34, bgcolor: brand.primary, color: "#FFFFFF", fontWeight: 700, fontSize: 14 }}>
                {user?.full_name?.charAt(0).toUpperCase() ?? "U"}
              </Avatar>
            </IconButton>
            <Menu anchorEl={userMenuAnchor} open={!!userMenuAnchor} onClose={() => setUserMenuAnchor(null)}>
              <Box sx={{ px: 2, py: 1 }}>
                <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{user?.full_name}</Typography>
                <Typography sx={{ fontSize: 12, color: palette.textSecondary, textTransform: "capitalize" }}>{user?.role}</Typography>
              </Box>
              <Divider />
              <MenuItem component={NavLink} to="/settings" onClick={() => setUserMenuAnchor(null)} sx={{ gap: 1.5 }}>
                <SettingsOutlinedIcon fontSize="small" /> Settings
              </MenuItem>
              <MenuItem onClick={logout} sx={{ gap: 1.5 }}>
                <LogoutOutlinedIcon fontSize="small" /> Log out
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        <Box sx={{ flexGrow: 1, p: { xs: 2, md: 4 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
