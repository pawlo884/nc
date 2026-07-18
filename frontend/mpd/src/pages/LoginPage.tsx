import axios from 'axios';
import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../components/Layout.css';

function loginErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { non_field_errors?: string[]; detail?: string; username?: string[]; password?: string[] }
      | string
      | undefined;

    if (typeof data === 'string' && data.trim()) {
      return data;
    }
    if (data && typeof data === 'object') {
      if (data.non_field_errors?.[0]) {
        return data.non_field_errors[0];
      }
      if (data.detail) {
        return data.detail;
      }
      if (data.username?.[0] || data.password?.[0]) {
        return [data.username?.[0], data.password?.[0]].filter(Boolean).join(' ');
      }
    }
    if (error.code === 'ERR_NETWORK') {
      return 'Brak połączenia z API (sprawdź Django na :8000).';
    }
    if (error.response?.status === 400) {
      return 'Nieprawidłowa nazwa użytkownika lub hasło.';
    }
    if (error.response?.status) {
      return `Błąd logowania (HTTP ${error.response.status}).`;
    }
  }
  return 'Nie udało się zalogować.';
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(loginErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>MPD</h1>
        <p>Zaloguj się kontem Django (username, nie e-mail).</p>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Nazwa użytkownika</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Hasło</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Logowanie…' : 'Zaloguj'}
          </button>
        </form>
      </div>
    </div>
  );
}
