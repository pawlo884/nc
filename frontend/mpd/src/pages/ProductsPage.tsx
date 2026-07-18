import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { deleteProduct, fetchCatalogBrands, fetchCatalogPaths, fetchProducts } from '../api/mpd';
import { ProductThumbnail } from '../components/ProductThumbnail';
import '../components/Layout.css';
import './ProductDetailPage.css';

const PAGE_SIZE = 50;

type SortField = 'id' | 'name' | 'brand_name' | 'visibility' | 'updated_at';
type VisibilityFilter = '' | 'true' | 'false';

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

function parseOptionalNumber(value: string): number | undefined {
  if (!value) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function ProductsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [brandId, setBrandId] = useState('');
  const [visibility, setVisibility] = useState<VisibilityFilter>('');
  const [pathId, setPathId] = useState('');
  const [sortField, setSortField] = useState<SortField>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [listError, setListError] = useState<string | null>(null);
  const searchTimerRef = useRef<number | undefined>(undefined);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const ordering = orderingParam(sortField, sortDir);
  const brandIdNum = parseOptionalNumber(brandId);
  const pathIdNum = parseOptionalNumber(pathId);
  const visibilityBool = visibility === 'true' ? true : visibility === 'false' ? false : undefined;

  const brandsQuery = useQuery({
    queryKey: ['mpd-catalog-brands'],
    queryFn: fetchCatalogBrands,
    staleTime: 5 * 60_000,
  });

  const pathsQuery = useQuery({
    queryKey: ['mpd-catalog-paths'],
    queryFn: fetchCatalogPaths,
    staleTime: 5 * 60_000,
  });

  const pathOptions = useMemo(() => {
    const rows = pathsQuery.data || [];
    return [...rows].sort((a, b) => {
      const left = `${a.path || ''} ${a.name || ''}`.trim();
      const right = `${b.path || ''} ${b.name || ''}`.trim();
      return left.localeCompare(right, 'pl');
    });
  }, [pathsQuery.data]);

  const { data, isLoading, isError, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ['mpd-products', debouncedSearch, brandIdNum, visibilityBool, pathIdNum, ordering],
      queryFn: ({ pageParam }) =>
        fetchProducts({
          search: debouncedSearch || undefined,
          brand_id: brandIdNum,
          visibility: visibilityBool,
          path_id: pathIdNum,
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
    setSortDir(field === 'id' || field === 'updated_at' ? 'desc' : 'asc');
  }

  function handleDelete(productId: number, productName: string) {
    const label = productName || `#${productId}`;
    if (!window.confirm(`Na pewno usunąć produkt „${label}” (ID ${productId})?`)) {
      return;
    }
    setListError(null);
    deleteMutation.mutate(productId);
  }

  function clearFilters() {
    setSearch('');
    setDebouncedSearch('');
    setBrandId('');
    setVisibility('');
    setPathId('');
  }

  const hasActiveFilters =
    Boolean(debouncedSearch) || Boolean(brandId) || Boolean(visibility) || Boolean(pathId);

  const products = data?.pages.flatMap(page => page.results) ?? [];
  const totalCount = data?.pages[0]?.count ?? 0;

  return (
    <div className="page-card">
      <h2 className="page-title">Produkty MPD</h2>
      <p className="page-subtitle">
        Lista produktów z filtrowaniem po marce, widoczności i kategorii (ścieżce).
      </p>

      <div className="toolbar toolbar--filters">
        <input
          type="search"
          className="search-input"
          placeholder="Szukaj po nazwie lub marce…"
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
        />
        <select
          className="filter-select"
          value={brandId}
          onChange={e => setBrandId(e.target.value)}
          aria-label="Filtr marki"
        >
          <option value="">Wszystkie marki</option>
          {(brandsQuery.data || []).map(brand => (
            <option key={brand.id} value={brand.id}>
              {brand.name || `Marka #${brand.id}`}
            </option>
          ))}
        </select>
        <select
          className="filter-select"
          value={visibility}
          onChange={e => setVisibility(e.target.value as VisibilityFilter)}
          aria-label="Filtr widoczności"
        >
          <option value="">Widoczność: wszystkie</option>
          <option value="true">Widoczne</option>
          <option value="false">Ukryte</option>
        </select>
        <select
          className="filter-select filter-select--wide"
          value={pathId}
          onChange={e => setPathId(e.target.value)}
          aria-label="Filtr kategorii"
        >
          <option value="">Wszystkie kategorie</option>
          {pathOptions.map(path => (
            <option key={path.id} value={path.id}>
              {path.name || '(brak nazwy)'} [{path.path || '-'}]
            </option>
          ))}
        </select>
        {hasActiveFilters && (
          <button type="button" className="btn btn-muted" onClick={clearFilters}>
            Wyczyść filtry
          </button>
        )}
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
