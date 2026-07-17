import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const API_BASE = "/api/v1";

export const apiClient = axios.create({ baseURL: API_BASE });

function getStoredTokens() {
  return {
    access: localStorage.getItem("smartops_access_token"),
    refresh: localStorage.getItem("smartops_refresh_token"),
  };
}

export function setStoredTokens(access: string, refresh: string) {
  localStorage.setItem("smartops_access_token", access);
  localStorage.setItem("smartops_refresh_token", refresh);
}

export function clearStoredTokens() {
  localStorage.removeItem("smartops_access_token");
  localStorage.removeItem("smartops_refresh_token");
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { access } = getStoredTokens();
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

let isRefreshing = false;
let pendingQueue: Array<() => void> = [];

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      const { refresh } = getStoredTokens();
      if (!refresh) {
        clearStoredTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue requests that arrive while a refresh is already in flight,
        // rather than firing a duplicate refresh call for each of them.
        return new Promise((resolve) => {
          pendingQueue.push(() => resolve(apiClient(originalRequest)));
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh });
        setStoredTokens(data.access_token, refresh);
        pendingQueue.forEach((cb) => cb());
        pendingQueue = [];
        return apiClient(originalRequest);
      } catch (refreshError) {
        clearStoredTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
