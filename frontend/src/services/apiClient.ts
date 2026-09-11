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

class ApiClient {
  private instance: AxiosInstance;

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
        const token = localStorage.getItem('auth_token');
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

    // Response interceptor for consistent error extraction
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError<any>) => {
        const errorResponse: ApiErrorDetail = {
          status: error.response?.status || 500,
          code: error.response?.data?.code || 'NETWORK_ERROR',
          message: error.response?.data?.message || error.message || 'An unexpected network error occurred',
          requestId: error.response?.headers?.['x-request-id'] || error.response?.data?.request_id,
          details: error.response?.data?.details,
        };
        console.error(`[API Error] [${errorResponse.code}]:`, errorResponse.message);
        return Promise.reject(errorResponse);
      }
    );
  }

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
