import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct } from '../api/mpd'
import '../components/Layout.css'
import './ProductDetailPage.css'

function MetaItem({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) {
    return null
  }
  return (
    <div className="product-meta__item">
      <span className="product-meta__label">{label}</span>
      <span className="product-meta__value">{value}</span>
    </div>
  )
}

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const productId = Number(id)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['mpd-product', productId],
    queryFn: () => fetchProduct(productId),
    enabled: Number.isFinite(productId) && productId > 0,
  })

  if (!Number.isFinite(productId) || productId <= 0) {
    return (
      <div className="page-card">
        <div className="alert alert-error">Nieprawidłowy identyfikator produktu.</div>
        <Link to="/" className="back-link">
          ← Wróć do listy
        </Link>
      </div>
    )
  }

  if (isLoading) {
    return <div className="loading">Ładowanie produktu…</div>
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
    )
  }

  const product = data.product

  return (
    <div className="product-detail">
      <Link to="/" className="back-link">
        ← Wróć do listy
      </Link>

      <div className="product-detail__header page-card">
        <div className="product-detail__title-row">
          <div>
            <p className="product-detail__id">ID: {product.id}</p>
            <h2 className="page-title">{product.name}</h2>
            {product.short_description && (
              <p className="product-detail__short">{product.short_description}</p>
            )}
          </div>
          <span
            className={`badge ${product.visibility ? 'badge-visible' : 'badge-hidden'}`}
          >
            {product.visibility ? 'Widoczny' : 'Ukryty'}
          </span>
        </div>

        <div className="product-meta">
          <MetaItem label="Marka" value={product.brand_name} />
          <MetaItem label="Kolekcja" value={product.collection_name} />
          <MetaItem label="Seria" value={product.series_name} />
          <MetaItem label="Sezon" value={product.season_name} />
          <MetaItem label="Jednostka" value={product.unit_name} />
          {product.updated_at && (
            <MetaItem
              label="Aktualizacja"
              value={new Date(product.updated_at).toLocaleString('pl-PL')}
            />
          )}
        </div>
      </div>

      <div className="product-detail__grid">
        {product.images.length > 0 && (
          <div className="page-card product-detail__images">
            <h3 className="section-title">Zdjęcia</h3>
            <div className="image-gallery">
              {product.images.map((img) => (
                <a
                  key={img.id}
                  href={img.image_url || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="image-gallery__item"
                >
                  {img.image_url ? (
                    <img src={img.image_url} alt={`Produkt ${product.id}`} loading="lazy" />
                  ) : (
                    <span className="image-gallery__fallback">Brak URL</span>
                  )}
                </a>
              ))}
            </div>
          </div>
        )}

        {product.description && (
          <div className="page-card product-detail__description">
            <h3 className="section-title">Opis</h3>
            <div className="product-description">{product.description}</div>
          </div>
        )}
      </div>

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
                {product.variants.map((variant) => (
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
  )
}
