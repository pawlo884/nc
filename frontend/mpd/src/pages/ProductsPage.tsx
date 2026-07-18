import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchProducts } from '../api/mpd';
import '../components/Layout.css';
import './ProductDetailPage.css';

export function ProductsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['mpd-products', debouncedSearch, page],
    queryFn: () =>
      fetchProducts({
        search: debouncedSearch || undefined,
        page,
        page_size: 50,
      }),
  });

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
    window.clearTimeout((window as unknown as { _searchTimer?: number })._searchTimer);
    (window as unknown as { _searchTimer?: number })._searchTimer = window.setTimeout(
      () => setDebouncedSearch(value),
      350
    );
  }

  const totalPages = data ? Math.ceil(data.count / 50) : 1;

  return (
    <div className="page-card">
      <h2 className="page-title">Produkty MPD</h2>
      <p className="page-subtitle">Lista produktów w bazie MPD z filtrowaniem po nazwie i marce.</p>

      <div className="toolbar">
        <input
          type="search"
          className="search-input"
          placeholder="Szukaj po nazwie lub marce…"
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
        />
      </div>

      {isLoading && <div className="loading">Ładowanie produktów…</div>}

      {isError && (
        <div className="alert alert-error">
          Błąd: {(error as Error).message || 'Nie udało się pobrać produktów.'}
        </div>
      )}

      {data && (
        <>
          <p style={{ color: '#666', marginBottom: '0.75rem' }}>
            Znaleziono: <strong>{data.count}</strong> produktów
          </p>
          <table className="data-table products-table">
            <thead>
              <tr>
                <th style={{ width: 70 }}>ID</th>
                <th>Nazwa</th>
                <th style={{ width: 180 }}>Marka</th>
                <th style={{ width: 100 }}>Widoczność</th>
                <th style={{ width: 160 }}>Aktualizacja</th>
              </tr>
            </thead>
            <tbody>
              {data.results.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">
                    Brak produktów spełniających kryteria.
                  </td>
                </tr>
              ) : (
                data.results.map(product => (
                  <tr key={product.id} onClick={() => navigate(`/products/${product.id}`)}>
                    <td>{product.id}</td>
                    <td>
                      <Link
                        to={`/products/${product.id}`}
                        className="products-table__link"
                        onClick={e => e.stopPropagation()}
                      >
                        {product.name}
                      </Link>
                    </td>
                    <td>{product.brand_name || '—'}</td>
                    <td>
                      <span
                        className={`badge ${product.visibility ? 'badge-visible' : 'badge-hidden'}`}
                      >
                        {product.visibility ? 'Tak' : 'Nie'}
                      </span>
                    </td>
                    <td>{new Date(product.updated_at).toLocaleString('pl-PL')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="pagination">
              <button type="button" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                ‹ Poprzednia
              </button>
              <span style={{ padding: '0.35rem 0.65rem', color: '#666' }}>
                Strona {page} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Następna ›
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
