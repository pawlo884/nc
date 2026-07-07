import axios from 'axios'

// Zapytania idą przez proxy Vite (/api -> Django na 127.0.0.1:8000),
// więc cookie sesji Django jest wysyłane automatycznie (same-origin).
export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})
