/**
 * API Client — Axios instance with dynamic base URL and Firebase Bearer token.
 * Automatically attaches auth token to every request.
 */

import axios from 'axios';
import { getAuth } from 'firebase/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes — tile fetching + YOLO inference can be slow
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach Firebase Bearer token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const auth = getAuth();
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      // Auth not initialized or no user — continue without token
      console.debug('No auth token available:', err.message);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      if (status === 401) {
        console.warn('Authentication required. Redirecting to login...');
        // Don't redirect automatically — let the app handle it
      }
      console.error(`API Error ${status}:`, data);
    } else if (error.request) {
      console.error('Network error — no response received:', error.message);
    } else {
      console.error('Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // Health check
  health: () => apiClient.get('/health'),

  // Scan viewport
  scanViewport: (bbox, zoom = 15) =>
    apiClient.post('/api/v1/scan-viewport', { bbox, zoom }),

  // Temporal analysis
  temporalAnalysis: (bbox, zoom = 15) =>
    apiClient.post('/api/v1/temporal-analysis', { bbox, zoom }),

  // Chat
  chat: (message, scanId = null) =>
    apiClient.post('/api/v1/chat', { message, scan_id: scanId }),

  // Upload file
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/api/v1/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Export report
  exportReport: (scanId, includeTemp = true, title = null) =>
    apiClient.post(
      '/api/v1/reports/export',
      { scan_id: scanId, include_temporal: includeTemp, title },
      { responseType: 'blob' }
    ),
};

export default apiClient;
