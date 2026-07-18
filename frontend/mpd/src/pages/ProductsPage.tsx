import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { deleteProduct, fetchProducts } from '../api/mpd';
import { ProductThumbnail } from '../components/ProductThumbnail';
import '../components/Layout.css';
import './ProductDetailPage.css';

const PAGE_SIZE = 50;

type SortField = 'id' | 'name' | 'brand_name' | 'visibility' | 'updated_at';

const SORTABLE_COLUMNS: { field: SortField; label: string; width?: number }[] = [
  { field: 'id', label: 'ID', width: 70 },
  { field: 'name', label: 'Nazwa' },
  { field: 'brand_name', label: 'Marka', width: 180 },
  { field: 'visibility', label: 'Widoczność', width: 100 },
  { field: 'updated_at', label: 'Aktualizacja', width: 160 },
];

function orderingParam(field: SortField, direction: 'asc' | 'desc'): string {
  return direction === 'desc' ? `-${field}` : field;
}

export function ProductsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortField, setSortField] = useState<SortField>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [listError, setListError] = useState<string | null>(null);
  const searchTimerRef = useRef<number | undefined>(undefined);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const ordering = orderingParam(sortField, sortDir);

  const { data, isLoading, isError, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ['mpd-products', debouncedSearch, ordering],
      queryFn: ({ pageParam }) =>
        fetchProducts({
          search: debouncedSearch || undefined,
          page: pageParam,
          page_size: PAGE_SIZE,
          ordering,
        }),
      initialPageParam: 1,
      getNextPageParam: (lastPage, _pages, lastPageParam) =>
        lastPage.next ? lastPageParam + 1 : undefined,
    });

  const deleteMutation = useMutation({
    mutationFn: (productId: number) => deleteProduct(productId),
    onSuccess: async result => {
      if (result.status === 'error') {
        setListError(result.message || 'Nie udało się usunąć produktu.');
        return;
      }
      setListError(null);
      await queryClient.invalidateQueries({ queryKey: ['mpd-products'] });
    },
    onError: err => {
      if (axios.isAxiosError(err)) {
        const message =
          (err.response?.data as { message?: string; detail?: string } | undefined)?.message ||
          (err.response?.data as { detail?: string } | undefined)?.detail ||
          err.message;
        setListError(message || 'Nie udało się usunąć produktu.');
        return;
      }
      setListError('Nie udało się usunąć produktu.');
    },
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

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortField(field);
    setSortDir(field === 'updated_at' ? 'desc' : 'asc');
  }

  function handleDelete(productId: number, productName: string) {
    const label = productName || `#${productId}`;
    if (!window.confirm(`Na pewno usunąć produkt „${label}” (ID ${productId})?`)) {
      return;
    }
    setListError(null);
    deleteMutation.mutate(productId);
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

      {listError && <div className="alert alert-error">{listError}</div>}

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
                {SORTABLE_COLUMNS.map(col => {
                  const active = sortField === col.field;
                  const ariaSort = active
                    ? sortDir === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : 'none';
                  return (
                    <th
                      key={col.field}
                      style={col.width ? { width: col.width } : undefined}
                      className={`sortable-th${active ? ' sortable-th--active' : ''}`}
                      aria-sort={ariaSort}
                    >
                      <button
                        type="button"
                        className="sortable-th__btn"
                        onClick={() => handleSort(col.field)}
                      >
                        <span>{col.label}</span>
                        <span className="sortable-th__indicator" aria-hidden>
                          {active ? (sortDir === 'asc' ? '▲' : '▼') : '⇅'}
                        </span>
                      </button>
                    </th>
                  );
                })}
                <th style={{ width: 90 }}>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">
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
                    <td>
                      <button
                        type="button"
                        className="btn btn-danger-sm"
                        disabled={deleteMutation.isPending}
                        onClick={e => {
                          e.stopPropagation();
                          handleDelete(product.id, product.name);
                        }}
                      >
                        Usuń
                      </button>
                    </td>
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
