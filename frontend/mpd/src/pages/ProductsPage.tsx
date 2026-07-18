import { useInfiniteQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchProducts } from '../api/mpd';
import { ProductThumbnail } from '../components/ProductThumbnail';
import '../components/Layout.css';
import './ProductDetailPage.css';

const PAGE_SIZE = 50;

export function ProductsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const searchTimerRef = useRef<number | undefined>(undefined);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const { data, isLoading, isError, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ['mpd-products', debouncedSearch],
      queryFn: ({ pageParam }) =>
        fetchProducts({
          search: debouncedSearch || undefined,
          page: pageParam,
          page_size: PAGE_SIZE,
        }),
      initialPageParam: 1,
      getNextPageParam: (lastPage, _pages, lastPageParam) =>
        lastPage.next ? lastPageParam + 1 : undefined,
    });

  useEffect(() => {
    const el = loadMoreRef.current;
    if (!el) {
      return;
    }
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      { rootMargin: '240px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, data?.pages.length]);

  function handleSearchChange(value: string) {
    setSearch(value);
    window.clearTimeout(searchTimerRef.current);
    searchTimerRef.current = window.setTimeout(() => setDebouncedSearch(value), 350);
  }

  const products = data?.pages.flatMap(page => page.results) ?? [];
  const totalCount = data?.pages[0]?.count ?? 0;

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
            Wyświetlono: <strong>{products.length}</strong> z <strong>{totalCount}</strong>{' '}
            produktów
          </p>
          <table className="data-table products-table">
            <thead>
              <tr>
                <th style={{ width: 72 }}>Zdjęcie</th>
                <th style={{ width: 70 }}>ID</th>
                <th>Nazwa</th>
                <th style={{ width: 180 }}>Marka</th>
                <th style={{ width: 100 }}>Widoczność</th>
                <th style={{ width: 160 }}>Aktualizacja</th>
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-state">
                    Brak produktów spełniających kryteria.
                  </td>
                </tr>
              ) : (
                products.map(product => (
                  <tr key={product.id} onClick={() => navigate(`/products/${product.id}`)}>
                    <td className="products-table__thumb-cell">
                      <ProductThumbnail
                        src={product.thumbnail_url}
                        alt={product.name || `Produkt ${product.id}`}
                      />
                    </td>
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

          <div ref={loadMoreRef} className="infinite-scroll-sentinel" aria-hidden={!hasNextPage}>
            {isFetchingNextPage && <div className="loading">Ładowanie kolejnych…</div>}
            {!hasNextPage && products.length > 0 && (
              <p className="infinite-scroll-end">Koniec listy</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
