import { apiClient } from "./client";
import type {
  AuthResponse,
  DashboardSummary,
  Equipment,
  PaginatedResponse,
  Recommendation,
} from "@/types/api";

export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const { data } = await apiClient.post<AuthResponse>("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },
  register: async (payload: {
    email: string;
    password: string;
    full_name: string;
    role?: string;
    department?: string;
    region?: string;
  }) => {
    const { data } = await apiClient.post("/auth/register", payload);
    return data;
  },
  me: async () => {
    const { data } = await apiClient.get("/auth/me");
    return data;
  },
};

export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const { data } = await apiClient.get<DashboardSummary>("/dashboard/summary");
    return data;
  },
};

export const equipmentApi = {
  list: async (params: {
    page?: number;
    page_size?: number;
    status?: string;
    region?: string;
    equipment_type?: string;
    search?: string;
  }): Promise<PaginatedResponse<Equipment>> => {
    const { data } = await apiClient.get<PaginatedResponse<Equipment>>("/equipment", { params });
    return data;
  },
  getById: async (id: string): Promise<Equipment> => {
    const { data } = await apiClient.get<Equipment>(`/equipment/${id}`);
    return data;
  },
  getPredictions: async (id: string) => {
    const { data } = await apiClient.get(`/equipment/${id}/predictions`);
    return data;
  },
  getRegions: async (): Promise<string[]> => {
    const { data } = await apiClient.get<string[]>("/equipment/meta/regions");
    return data;
  },
  getTypes: async (): Promise<string[]> => {
    const { data } = await apiClient.get<string[]>("/equipment/meta/types");
    return data;
  },
};

export const decisionsApi = {
  list: async (params: { page?: number; page_size?: number; category?: string; status?: string }): Promise<PaginatedResponse<Recommendation>> => {
    const { data } = await apiClient.get<PaginatedResponse<Recommendation>>("/decisions", { params });
    return data;
  },
  updateStatus: async (id: string, newStatus: string) => {
    const { data } = await apiClient.patch(`/decisions/${id}/status`, null, { params: { new_status: newStatus } });
    return data;
  },
};

export const forecastsApi = {
  getDemand: async (granularity: string, region?: string) => {
    const { data } = await apiClient.get("/forecasts/demand", { params: { granularity, region } });
    return data;
  },
  getRevenue: async (granularity: string) => {
    const { data } = await apiClient.get("/forecasts/revenue", { params: { granularity } });
    return data;
  },
};
