import { Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Layout.css';

export function Layout() {
  const { logout, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <h1>MPD</h1>
          <span>Master Product Database</span>
        </div>
        <button type="button" className="btn btn-secondary" onClick={logout}>
          Wyloguj
        </button>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
