import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchProduct, updateProduct } from '../api/mpd';
import { ProductExtrasPanels } from '../components/ProductExtrasPanels';
import type { MpdProductDetail, MpdProductUpdatePayload } from '../types/mpd';
import '../components/Layout.css';
import './ProductDetailPage.css';

function parseOptionalId(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildFormState(product: MpdProductDetail) {
  return {
    name: product.name ?? '',
    short_description: product.short_description ?? '',
    description: product.description ?? '',
    brand_id: product.brand_id != null ? String(product.brand_id) : '',
    collection_id: product.collection_id != null ? String(product.collection_id) : '',
    series_id: product.series_id != null ? String(product.series_id) : '',
    season_id: product.season_id != null ? String(product.season_id) : '',
    unit_id: product.unit_id != null ? String(product.unit_id) : '',
    visibility: Boolean(product.visibility),
  };
}

type FormState = ReturnType<typeof buildFormState>;

function formsEqual(a: FormState, b: FormState): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(() => ({
    name: '',
    short_description: '',
    description: '',
    brand_id: '',
    collection_id: '',
    series_id: '',
    season_id: '',
    unit_id: '',
    visibility: true,
  }));
  const [baseline, setBaseline] = useState<FormState | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['mpd-product', productId],
    queryFn: () => fetchProduct(productId),
    enabled: Number.isFinite(productId) && productId > 0,
  });

  useEffect(() => {
    if (data?.product) {
      const next = buildFormState(data.product);
      setForm(next);
      setBaseline(next);
    }
  }, [data?.product]);

  const saveMutation = useMutation({
    mutationFn: (payload: MpdProductUpdatePayload) => updateProduct(productId, payload),
    onSuccess: async result => {
      if (result.status === 'error') {
        setSaveError(result.message || 'Nie udało się zapisać produktu.');
        return;
      }
      setSaveError(null);
      setSaveOk('Zapisano zmiany.');
      await queryClient.invalidateQueries({ queryKey: ['mpd-product', productId] });
      await queryClient.invalidateQueries({ queryKey: ['mpd-products'] });
    },
    onError: err => {
      if (axios.isAxiosError(err)) {
        const message =
          (err.response?.data as { message?: string; detail?: string } | undefined)?.message ||
          (err.response?.data as { detail?: string } | undefined)?.detail ||
          err.message;
        setSaveError(message || 'Nie udało się zapisać produktu.');
        return;
      }
      setSaveError('Nie udało się zapisać produktu.');
    },
  });

  if (!Number.isFinite(productId) || productId <= 0) {
    return (
      <div className="page-card">
        <div className="alert alert-error">Nieprawidłowy identyfikator produktu.</div>
        <Link to="/" className="back-link">
          ← Wróć do listy
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return <div className="loading">Ładowanie produktu…</div>;
  }

  if (isError || data?.status === 'error' || !data?.product) {
    return (
      <div className="page-card">
        <div className="alert alert-error">
          {(error as Error)?.message || data?.message || 'Nie udało się pobrać produktu.'}
        </div>
        <Link to="/" className="back-link">
          ← Wróć do listy
        </Link>
      </div>
    );
  }

  const product = data.product;
  const dirty = baseline ? !formsEqual(form, baseline) : false;

  function handleReset() {
    if (!baseline) {
      return;
    }
    setForm(baseline);
    setSaveError(null);
    setSaveOk(null);
  }

  function handleSave() {
    setSaveError(null);
    setSaveOk(null);
    if (!form.name.trim()) {
      setSaveError('Nazwa produktu jest wymagana.');
      return;
    }
    saveMutation.mutate({
      name: form.name.trim(),
      short_description: form.short_description.trim() || null,
      description: form.description.trim() || null,
      brand_id: parseOptionalId(form.brand_id),
      collection_id: parseOptionalId(form.collection_id),
      series_id: parseOptionalId(form.series_id),
      season_id: parseOptionalId(form.season_id),
      unit_id: parseOptionalId(form.unit_id),
      visibility: form.visibility,
    });
  }

  return (
    <div className="product-detail">
      <div className="product-detail__nav">
        <Link to="/" className="back-link">
          ← Wróć do listy
        </Link>
        <div className="product-detail__actions">
          <button
            type="button"
            className="btn btn-muted"
            onClick={handleReset}
            disabled={!dirty || saveMutation.isPending}
          >
            Cofnij
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!dirty || saveMutation.isPending}
          >
            {saveMutation.isPending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
        </div>
      </div>

      {saveError && <div className="alert alert-error">{saveError}</div>}
      {saveOk && <div className="alert alert-success">{saveOk}</div>}

      <div className="product-detail__header page-card">
        <div className="product-detail__title-row">
          <div style={{ flex: 1 }}>
            <p className="product-detail__id">ID: {product.id}</p>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="product-name">Nazwa</label>
                <input
                  id="product-name"
                  className="search-input"
                  value={form.name}
                  onChange={e => {
                    setSaveOk(null);
                    setForm(prev => ({ ...prev, name: e.target.value }));
                  }}
                />
              </div>
              <div className="form-group">
                <label htmlFor="product-short">Krótki opis</label>
                <input
                  id="product-short"
                  className="search-input"
                  value={form.short_description}
                  onChange={e => {
                    setSaveOk(null);
                    setForm(prev => ({ ...prev, short_description: e.target.value }));
                  }}
                />
              </div>
            </div>
          </div>
          <label className="visibility-toggle">
            <input
              type="checkbox"
              checked={form.visibility}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, visibility: e.target.checked }));
              }}
            />
            Widoczny
          </label>
        </div>

        <div className="form-grid form-grid--meta">
          <div className="form-group">
            <label htmlFor="brand-id">
              Marka ID{product.brand_name ? ` (${product.brand_name})` : ''}
            </label>
            <input
              id="brand-id"
              className="search-input"
              inputMode="numeric"
              value={form.brand_id}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, brand_id: e.target.value }));
              }}
            />
          </div>
          <div className="form-group">
            <label htmlFor="collection-id">
              Kolekcja ID{product.collection_name ? ` (${product.collection_name})` : ''}
            </label>
            <input
              id="collection-id"
              className="search-input"
              inputMode="numeric"
              value={form.collection_id}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, collection_id: e.target.value }));
              }}
            />
          </div>
          <div className="form-group">
            <label htmlFor="series-id">
              Seria ID{product.series_name ? ` (${product.series_name})` : ''}
            </label>
            <input
              id="series-id"
              className="search-input"
              inputMode="numeric"
              value={form.series_id}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, series_id: e.target.value }));
              }}
            />
          </div>
          <div className="form-group">
            <label htmlFor="season-id">
              Sezon ID{product.season_name ? ` (${product.season_name})` : ''}
            </label>
            <input
              id="season-id"
              className="search-input"
              inputMode="numeric"
              value={form.season_id}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, season_id: e.target.value }));
              }}
            />
          </div>
          <div className="form-group">
            <label htmlFor="unit-id">
              Jednostka ID{product.unit_name ? ` (${product.unit_name})` : ''}
            </label>
            <input
              id="unit-id"
              className="search-input"
              inputMode="numeric"
              value={form.unit_id}
              onChange={e => {
                setSaveOk(null);
                setForm(prev => ({ ...prev, unit_id: e.target.value }));
              }}
            />
          </div>
        </div>
      </div>

      <div className="product-detail__grid">
        {product.images.length > 0 && (
          <div className="page-card product-detail__images">
            <h3 className="section-title">Zdjęcia</h3>
            <div className="image-gallery">
              {product.images.map(img => (
                <a
                  key={img.id}
                  href={img.image_url || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="image-gallery__item"
                >
                  {img.image_url ? (
                    <img
                      src={img.image_url}
                      alt={`Produkt ${product.id}`}
                      loading="lazy"
                      decoding="async"
                      width={120}
                      height={120}
                      onError={e => {
                        const el = e.currentTarget;
                        el.onerror = null;
                        el.src =
                          'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5icmFrIHpkajwvdGV4dD48L3N2Zz4=';
                      }}
                    />
                  ) : (
                    <span className="image-gallery__fallback">Brak URL</span>
                  )}
                </a>
              ))}
            </div>
          </div>
        )}

        <div className="page-card product-detail__description">
          <h3 className="section-title">Opis</h3>
          <textarea
            className="description-editor"
            rows={12}
            value={form.description}
            onChange={e => {
              setSaveOk(null);
              setForm(prev => ({ ...prev, description: e.target.value }));
            }}
          />
        </div>
      </div>

      <ProductExtrasPanels productId={productId} product={product} />

      <div className="page-card product-detail__variants">
        <h3 className="section-title">
          Warianty
          <span className="section-count">{product.variants.length}</span>
        </h3>

        {product.variants.length === 0 ? (
          <div className="empty-state">Brak wariantów dla tego produktu.</div>
        ) : (
          <div className="variants-table-wrap">
            <table className="data-table variants-table">
              <thead>
                <tr>
                  <th style={{ width: 70 }}>ID</th>
                  <th>Kolor</th>
                  <th style={{ width: 120 }}>Rozmiar</th>
                  <th style={{ width: 80 }}>Stan</th>
                  <th style={{ width: 110 }}>Cena mag.</th>
                  <th style={{ width: 110 }}>Cena detal.</th>
                  <th style={{ width: 130 }}>Kod prod.</th>
                  <th style={{ width: 80 }}>IAI</th>
                </tr>
              </thead>
              <tbody>
                {product.variants.map(variant => (
                  <tr key={variant.variant_id}>
                    <td>{variant.variant_id}</td>
                    <td>
                      {variant.color_name ? (
                        <div className="color-info">
                          <span
                            className="color-dot"
                            style={{ backgroundColor: variant.hex_code || '#ccc' }}
                          />
                          <span>{variant.color_name}</span>
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{variant.size_name || <span className="muted">—</span>}</td>
                    <td>{variant.stock ?? <span className="muted">0</span>}</td>
                    <td>
                      {variant.warehouse_price != null ? (
                        `${variant.warehouse_price} PLN`
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {variant.price?.retail_price != null ? (
                        `${variant.price.retail_price} ${variant.price.currency || 'PLN'}`
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{variant.producer_code || <span className="muted">—</span>}</td>
                    <td>
                      <span
                        className={`badge ${variant.exported_to_iai ? 'badge-visible' : 'badge-hidden'}`}
                      >
                        {variant.exported_to_iai ? 'Tak' : 'Nie'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
