// Centralized API Client with JWT Token Management & Concurrency-Safe Refresh

const TOKEN_KEY = 'ahoum_access_token';
const REFRESH_KEY = 'ahoum_refresh_token';
const USER_KEY = 'ahoum_user';

export class ApiError extends Error {
  constructor(message, status, code, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code || 'error';
    this.details = details;
  }
}

// Token Storage Helpers
export const getAccessToken = () => localStorage.getItem(TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);
export const getStoredUser = () => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
};

export const setAuthData = (access, refresh, user) => {
  if (access) localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearAuthData = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
};

// Concurrency-safe refresh coordination
let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onTokenRefreshed = (newAccessToken) => {
  refreshSubscribers.forEach((cb) => cb(newAccessToken));
  refreshSubscribers = [];
};

const onRefreshFailed = () => {
  refreshSubscribers = [];
  clearAuthData();
  if (window.location.pathname !== '/login') {
    window.location.href = '/login?expired=1';
  }
};

/**
 * Executes a token refresh call to /api/auth/refresh/
 */
const performTokenRefresh = async () => {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error('No refresh token available');
  }

  const response = await fetch('/api/auth/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh })
  });

  if (!response.ok) {
    throw new Error('Refresh token invalid or expired');
  }

  const data = await response.json();
  const newAccess = data.access;
  localStorage.setItem(TOKEN_KEY, newAccess);
  return newAccess;
};

/**
 * Central API Request Function
 */
export async function apiRequest(endpoint, options = {}, isRetry = false) {
  const url = endpoint.startsWith('http') ? endpoint : endpoint;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers
    });
  } catch (netErr) {
    throw new ApiError('Unable to reach server. Please check your connection.', 0, 'network_error');
  }

  // Handle 401 Unauthorized - Attempt Token Refresh
  if (response.status === 401 && !isRetry && !endpoint.includes('/auth/')) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const newAccessToken = await performTokenRefresh();
        isRefreshing = false;
        onTokenRefreshed(newAccessToken);
        // Retry the original request with the fresh token
        return apiRequest(endpoint, options, true);
      } catch (refreshErr) {
        isRefreshing = false;
        onRefreshFailed();
        throw new ApiError('Session expired. Please log in again.', 401, 'session_expired');
      }
    } else {
      // Queue request until refresh resolves
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh((newAccessToken) => {
          if (!newAccessToken) {
            return reject(new ApiError('Session expired. Please log in again.', 401, 'session_expired'));
          }
          resolve(apiRequest(endpoint, options, true));
        });
      });
    }
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }
  }

  if (!response.ok) {
    let errorCode = 'error';
    let errorMessage = response.statusText || 'Request failed';
    let details = null;

    if (data && data.error) {
      errorCode = data.error.code || errorCode;
      errorMessage = data.error.message || errorMessage;
      details = data.error.details || null;
    } else if (data && typeof data === 'object') {
      if (data.detail) errorMessage = data.detail;
      if (data.code) errorCode = data.code;
    }

    throw new ApiError(errorMessage, response.status, errorCode, details);
  }

  return data;
}

export const api = {
  get: (url, headers = {}) => apiRequest(url, { method: 'GET', headers }),
  post: (url, body, headers = {}) => apiRequest(url, { method: 'POST', body: JSON.stringify(body), headers }),
  patch: (url, body, headers = {}) => apiRequest(url, { method: 'PATCH', body: JSON.stringify(body), headers }),
  delete: (url, headers = {}) => apiRequest(url, { method: 'DELETE', headers })
};
