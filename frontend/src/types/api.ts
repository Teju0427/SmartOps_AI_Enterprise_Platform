export type EquipmentStatus = "healthy" | "warning" | "critical";
export type RentalAvailability = "available" | "rented" | "in_maintenance" | "retired" | "in_transit";

export interface Equipment {
  id: string;
  machine_id: string;
  asset_tag: string;
  name: string;
  equipment_type: string;
  manufacturer: string;
  model_number: string;
  health_score: number | null;
  status: EquipmentStatus;
  availability: RentalAvailability;
  current_region: string;
  base_daily_rate: number;
  total_operating_hours: number;
  purchase_date: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardSummary {
  equipment: {
    total: number;
    available: number;
    critical_count: number;
    warning_count: number;
    avg_health_score: number | null;
  };
  financial: {
    total_historical_revenue: number;
    total_historical_profit: number;
    active_rentals: number;
    overdue_rentals: number;
  };
  customers: {
    total: number;
    top_customers: { name: string; revenue: number }[];
  };
  alerts_and_decisions: {
    pending_recommendations: number;
    unresolved_alerts: number;
  };
  regional_breakdown: { region: string; equipment_count: number }[];
}

export interface Recommendation {
  id: string;
  category: string;
  status: string;
  title: string;
  summary: string;
  detailed_reasoning: string;
  priority_score: number;
  confidence_score: number;
  estimated_impact_value: number | null;
  estimated_impact_metric: string | null;
  equipment_id: string | null;
  customer_id: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  department: string | null;
  region: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}
