import axios from 'axios';

const TOKEN_KEY = 'mpd_auth_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(config => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

function loginHref(): string {
  return `${import.meta.env.BASE_URL}login`;
}

function isLoginPath(pathname: string): boolean {
  return pathname === '/login' || pathname.endsWith('/login') || pathname.endsWith('/login/');
}

apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      clearStoredToken();
      if (!isLoginPath(window.location.pathname)) {
        window.location.href = loginHref();
      }
    }
    return Promise.reject(error);
  }
);
