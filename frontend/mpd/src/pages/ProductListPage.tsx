import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchProducts } from '../api/products'
import ApiError from '../components/ApiError'

const PAGE_SIZE = 50

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('pl-PL')
}

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const page = Math.max(1, Number(searchParams.get('page') ?? '1') || 1)
  const search = searchParams.get('search') ?? ''
  const [searchInput, setSearchInput] = useState(search)

  const { data, isPending, isError, error, isFetching } = useQuery({
    queryKey: ['products', { page, search }],
    queryFn: () =>
      fetchProducts({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
      }),
    placeholderData: keepPreviousData,
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1

  const goToPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', String(nextPage))
    setSearchParams(params)
  }

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams()
    if (searchInput.trim()) params.set('search', searchInput.trim())
    params.set('page', '1')
    setSearchParams(params)
  }

  return (
    <section>
      <div className="page-head">
        <h1>Produkty MPD</h1>
        {data && (
          <span className="badge">
            {data.count} {data.count === 1 ? 'produkt' : 'produktów'}
          </span>
        )}
      </div>

      <form className="toolbar" onSubmit={submitSearch}>
        <input
          type="search"
          placeholder="Szukaj po nazwie produktu lub marki…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit">Szukaj</button>
        {search && (
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setSearchInput('')
              setSearchParams({})
            }}
          >
            Wyczyść
          </button>
        )}
      </form>

      {isPending && <div className="loading">Ładowanie produktów…</div>}
      {isError && <ApiError error={error} />}

      {data && (
        <>
          <div className={`table-wrap${isFetching ? ' is-fetching' : ''}`}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nazwa</th>
                  <th>Marka</th>
                  <th>Widoczność</th>
                  <th>Utworzono</th>
                  <th>Zaktualizowano</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty">
                      Brak produktów spełniających kryteria.
                    </td>
                  </tr>
                )}
                {data.results.map((product) => (
                  <tr key={product.id}>
                    <td>{product.id}</td>
                    <td>
                      <Link to={`/products/${product.id}`}>{product.name}</Link>
                    </td>
                    <td>{product.brand_name ?? '—'}</td>
                    <td>
                      <span
                        className={`pill ${product.visibility ? 'pill-on' : 'pill-off'}`}
                      >
                        {product.visibility ? 'widoczny' : 'ukryty'}
                      </span>
                    </td>
                    <td>{formatDate(product.created_at)}</td>
                    <td>{formatDate(product.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <nav className="pagination">
            <button
              type="button"
              disabled={!data.previous}
              onClick={() => goToPage(page - 1)}
            >
              ← Poprzednia
            </button>
            <span>
              Strona {page} z {totalPages}
            </span>
            <button
              type="button"
              disabled={!data.next}
              onClick={() => goToPage(page + 1)}
            >
              Następna →
            </button>
          </nav>
        </>
      )}
    </section>
  )
}
