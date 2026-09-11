/**
 * Production API Client for SupplyChainAgent Frontend.
 *
 * Configured via VITE_API_URL, attaches correlation IDs,
 * handles token authorization, and standardizes error responses.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

// Get backend URL from environment or default to unified port 8000
const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
  requestId?: string;
}

export interface ApiErrorDetail {
  status: number;
  code: string;
  message: string;
  requestId?: string;
  details?: Record<string, any>;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

export interface UserProfile {
  id: string;
  organization_id: string;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

class ApiClient {
  private instance: AxiosInstance;
  private isRefreshing: boolean = false;

  constructor() {
    this.instance = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for Auth and Correlation headers
    this.instance.interceptors.request.use(
      (config) => {
        // Attach JWT token if present in localStorage
        const token = this.getAccessToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Generate client-side request correlation UUID if missing
        if (config.headers && !config.headers['X-Request-ID']) {
          config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for consistent error extraction and 401 handling
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError<any>) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          const refreshToken = this.getRefreshToken();

          if (refreshToken && !this.isRefreshing) {
            this.isRefreshing = true;
            try {
              const res = await axios.post<AuthTokens>(`${BASE_URL}/api/v1/auth/refresh`, {
                refresh_token: refreshToken,
              });
              this.setTokens(res.data);
              this.isRefreshing = false;

              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
              }
              return this.instance(originalRequest);
            } catch (refreshErr) {
              this.isRefreshing = false;
              this.clearTokens();
            }
          } else {
            this.clearTokens();
          }
        }

        const errorResponse: ApiErrorDetail = {
          status: error.response?.status || 500,
          code: error.response?.data?.code || error.response?.data?.error_code || 'NETWORK_ERROR',
          message: error.response?.data?.message || error.message || 'An unexpected network error occurred',
          requestId: error.response?.headers?.['x-request-id'] || error.response?.data?.request_id,
          details: error.response?.data?.details,
        };
        console.error(`[API Error] [${errorResponse.code}]:`, errorResponse.message);
        return Promise.reject(errorResponse);
      }
    );
  }

  // Token Management
  public getAccessToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  public getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  public setTokens(tokens: AuthTokens): void {
    localStorage.setItem('auth_token', tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem('refresh_token', tokens.refresh_token);
    }
  }

  public clearTokens(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
  }

  // Authentication API Methods
  public async login(email: string, password: string): Promise<AuthTokens> {
    const tokens = await this.post<AuthTokens>('/api/v1/auth/login', { email, password });
    this.setTokens(tokens);
    return tokens;
  }

  public async register(payload: {
    organization_name: string;
    email: string;
    password: string;
    full_name?: string;
    role?: string;
  }): Promise<UserProfile> {
    return await this.post<UserProfile>('/api/v1/auth/register', payload);
  }

  public async getMe(): Promise<UserProfile> {
    return await this.get<UserProfile>('/api/v1/auth/me');
  }

  public logout(): void {
    this.clearTokens();
  }

  // HTTP Verbs
  public async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.get<T>(url, config);
    return response.data;
  }

  public async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.post<T>(url, data, config);
    return response.data;
  }

  public async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.put<T>(url, data, config);
    return response.data;
  }

  public async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.delete<T>(url, config);
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;
