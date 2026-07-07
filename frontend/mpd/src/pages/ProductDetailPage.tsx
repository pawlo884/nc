import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct } from '../api/products'
import ApiError from '../components/ApiError'

function formatPrice(value: number | null, currency: string | null): string {
  if (value === null) return '—'
  return `${value.toFixed(2)} ${currency ?? ''}`.trim()
}

export default function ProductDetailPage() {
  const { productId } = useParams()
  const id = Number(productId)

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['product', id],
    queryFn: () => fetchProduct(id),
    enabled: Number.isFinite(id),
  })

  if (isPending) return <div className="loading">Ładowanie produktu…</div>
  if (isError) return <ApiError error={error} />

  const product = data.product

  return (
    <section>
      <Link to="/" className="back-link">
        ← Wróć do listy
      </Link>

      <div className="page-head">
        <h1>{product.name}</h1>
        <span className={`pill ${product.visibility ? 'pill-on' : 'pill-off'}`}>
          {product.visibility ? 'widoczny' : 'ukryty'}
        </span>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h2>Informacje</h2>
          <dl>
            <dt>ID</dt>
            <dd>{product.id}</dd>
            <dt>Marka (ID)</dt>
            <dd>{product.brand_id ?? '—'}</dd>
            <dt>Seria (ID)</dt>
            <dd>{product.series_id ?? '—'}</dd>
            <dt>Jednostka (ID)</dt>
            <dd>{product.unit_id ?? '—'}</dd>
            <dt>Krótki opis</dt>
            <dd>{product.short_description || '—'}</dd>
            <dt>Opis</dt>
            <dd className="prewrap">{product.description || '—'}</dd>
          </dl>
        </div>

        <div className="card">
          <h2>Klasyfikacja</h2>
          <dl>
            <dt>Ścieżki (ID)</dt>
            <dd>{product.paths.length ? product.paths.join(', ') : '—'}</dd>
            <dt>Atrybuty (ID)</dt>
            <dd>
              {product.attributes.length ? product.attributes.join(', ') : '—'}
            </dd>
          </dl>
        </div>
      </div>

      <div className="card">
        <h2>Warianty ({product.variants.length})</h2>
        {product.variants.length === 0 ? (
          <p className="empty">Produkt nie ma wariantów.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID wariantu</th>
                  <th>Kolor (ID)</th>
                  <th>Rozmiar (ID)</th>
                  <th>Kod producenta</th>
                  <th>Cena detaliczna</th>
                  <th>Cena netto</th>
                  <th>VAT</th>
                  <th>Eksport IAI</th>
                </tr>
              </thead>
              <tbody>
                {product.variants.map((variant) => (
                  <tr key={variant.variant_id}>
                    <td>{variant.variant_id}</td>
                    <td>{variant.color_id ?? '—'}</td>
                    <td>{variant.size_id ?? '—'}</td>
                    <td>{variant.producer_code || '—'}</td>
                    <td>
                      {formatPrice(
                        variant.price?.retail_price ?? null,
                        variant.price?.currency ?? null,
                      )}
                    </td>
                    <td>
                      {formatPrice(
                        variant.price?.net_price ?? null,
                        variant.price?.currency ?? null,
                      )}
                    </td>
                    <td>
                      {variant.price?.vat !== null &&
                      variant.price?.vat !== undefined
                        ? `${variant.price.vat}%`
                        : '—'}
                    </td>
                    <td>
                      <span
                        className={`pill ${variant.exported_to_iai ? 'pill-on' : 'pill-off'}`}
                      >
                        {variant.exported_to_iai ? 'tak' : 'nie'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
