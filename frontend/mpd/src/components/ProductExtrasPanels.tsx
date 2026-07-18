import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchCatalogAttributes,
  fetchCatalogFabricComponents,
  fetchCatalogPaths,
  fetchCatalogVats,
  manageProductAttributes,
  manageProductFabric,
  manageProductPaths,
  updateRetailPrices,
} from '../api/mpd'
import type { MpdProductDetail, MpdRetailPriceItem } from '../types/mpd'

function errorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { message?: string; detail?: string } | undefined
    return data?.message || data?.detail || err.message || fallback
  }
  return fallback
}

export function ProductExtrasPanels({
  productId,
  product,
}: {
  productId: number
  product: MpdProductDetail
}) {
  const queryClient = useQueryClient()
  const [sectionError, setSectionError] = useState<string | null>(null)
  const [sectionOk, setSectionOk] = useState<string | null>(null)

  const [attrToAdd, setAttrToAdd] = useState('')
  const [fabricToAdd, setFabricToAdd] = useState('')
  const [fabricPct, setFabricPct] = useState('100')
  const [pathFilter, setPathFilter] = useState('')
  const [retailDraft, setRetailDraft] = useState<Record<number, MpdRetailPriceItem>>({})
  const [bulkRetail, setBulkRetail] = useState('')

  const attrsCatalog = useQuery({
    queryKey: ['mpd-catalog-attributes'],
    queryFn: fetchCatalogAttributes,
  })
  const fabricCatalog = useQuery({
    queryKey: ['mpd-catalog-fabric'],
    queryFn: fetchCatalogFabricComponents,
  })
  const pathsCatalog = useQuery({
    queryKey: ['mpd-catalog-paths'],
    queryFn: fetchCatalogPaths,
  })
  const vatsCatalog = useQuery({
    queryKey: ['mpd-catalog-vats'],
    queryFn: fetchCatalogVats,
  })

  const defaultVatId = useMemo(() => {
    const rows = vatsCatalog.data || []
    if (rows.some((v) => v.id === 1)) {
      return 1
    }
    return rows[0]?.id ?? 1
  }, [vatsCatalog.data])

  useEffect(() => {
    const next: Record<number, MpdRetailPriceItem> = {}
    for (const variant of product.variants) {
      const vatId = variant.price?.vat_id ?? variant.price?.vat ?? defaultVatId
      next[variant.variant_id] = {
        variant_id: variant.variant_id,
        retail_price: variant.price?.retail_price ?? '',
        vat: vatId,
        vat_id: vatId,
        currency: variant.price?.currency || 'PLN',
      }
    }
    setRetailDraft(next)
  }, [product.variants, defaultVatId])

  function invalidateProduct() {
    return queryClient.invalidateQueries({ queryKey: ['mpd-product', productId] })
  }

  const assignedAttrIds = useMemo(
    () => new Set((product.attributes || []).map((a) => a.id)),
    [product.attributes],
  )
  const assignedFabricIds = useMemo(
    () => new Set((product.fabric || []).map((f) => f.component_id)),
    [product.fabric],
  )
  const assignedPathIds = useMemo(
    () => new Set((product.paths || []).map((p) => p.id)),
    [product.paths],
  )

  const availableAttributes = (attrsCatalog.data || []).filter((a) => !assignedAttrIds.has(a.id))
  const availableFabric = (fabricCatalog.data || []).filter((f) => !assignedFabricIds.has(f.id))
  const filteredPaths = (pathsCatalog.data || []).filter((p) => {
    if (!pathFilter.trim()) {
      return true
    }
    const q = pathFilter.toLowerCase()
    return (
      String(p.id).includes(q) ||
      (p.name || '').toLowerCase().includes(q) ||
      (p.path || '').toLowerCase().includes(q)
    )
  })

  const fabricTotal = (product.fabric || []).reduce((sum, item) => sum + (item.percentage || 0), 0)

  const attrMutation = useMutation({
    mutationFn: manageProductAttributes,
    onSuccess: async (res) => {
      if (res.status === 'error') {
        setSectionError(res.message || 'Błąd atrybutów')
        return
      }
      setSectionError(null)
      setSectionOk(res.message || 'Atrybuty zaktualizowane')
      setAttrToAdd('')
      await invalidateProduct()
    },
    onError: (err) => setSectionError(errorMessage(err, 'Błąd atrybutów')),
  })

  const fabricMutation = useMutation({
    mutationFn: manageProductFabric,
    onSuccess: async (res) => {
      if (res.status === 'error') {
        setSectionError(res.message || 'Błąd składu')
        return
      }
      setSectionError(null)
      setSectionOk(res.message || 'Skład zaktualizowany')
      setFabricToAdd('')
      await invalidateProduct()
    },
    onError: (err) => setSectionError(errorMessage(err, 'Błąd składu')),
  })

  const pathMutation = useMutation({
    mutationFn: manageProductPaths,
    onSuccess: async (res) => {
      if (res.status === 'error') {
        setSectionError(res.message || 'Błąd ścieżek')
        return
      }
      setSectionError(null)
      setSectionOk(res.message || 'Ścieżki zaktualizowane')
      await invalidateProduct()
    },
    onError: (err) => setSectionError(errorMessage(err, 'Błąd ścieżek')),
  })

  const retailMutation = useMutation({
    mutationFn: (prices: MpdRetailPriceItem[]) => updateRetailPrices(productId, prices),
    onSuccess: async (res) => {
      if (res.status === 'error') {
        setSectionError(res.message || 'Błąd cen')
        return
      }
      setSectionError(null)
      setSectionOk(res.message || 'Ceny zapisane')
      await invalidateProduct()
    },
    onError: (err) => setSectionError(errorMessage(err, 'Błąd cen')),
  })

  return (
    <>
      {sectionError && <div className="alert alert-error">{sectionError}</div>}
      {sectionOk && <div className="alert alert-success">{sectionOk}</div>}

      <div className="page-card">
        <h3 className="section-title">Atrybuty</h3>
        <div className="inline-add">
          <select
            className="search-input"
            value={attrToAdd}
            onChange={(e) => setAttrToAdd(e.target.value)}
          >
            <option value="">Wybierz atrybut…</option>
            {availableAttributes.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!attrToAdd || attrMutation.isPending}
            onClick={() => {
              setSectionOk(null)
              attrMutation.mutate({
                product_id: productId,
                action: 'add',
                attribute_ids: [Number(attrToAdd)],
              })
            }}
          >
            Dodaj
          </button>
        </div>
        {(product.attributes || []).length === 0 ? (
          <div className="empty-state">Brak atrybutów.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 80 }}>ID</th>
                <th>Nazwa</th>
                <th style={{ width: 100 }}>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {product.attributes.map((attr) => (
                <tr key={attr.id}>
                  <td>{attr.id}</td>
                  <td>{attr.name || '—'}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-danger-sm"
                      disabled={attrMutation.isPending}
                      onClick={() => {
                        setSectionOk(null)
                        attrMutation.mutate({
                          product_id: productId,
                          action: 'remove',
                          attribute_id: attr.id,
                        })
                      }}
                    >
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="page-card">
        <h3 className="section-title">
          Skład materiałowy
          <span className={`section-count ${fabricTotal === 100 ? '' : 'section-count--warn'}`}>
            {fabricTotal}%
          </span>
        </h3>
        <div className="inline-add">
          <select
            className="search-input"
            value={fabricToAdd}
            onChange={(e) => setFabricToAdd(e.target.value)}
          >
            <option value="">Wybierz komponent…</option>
            {availableFabric.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <input
            className="search-input"
            style={{ maxWidth: 100 }}
            type="number"
            min={1}
            max={100}
            value={fabricPct}
            onChange={(e) => setFabricPct(e.target.value)}
            placeholder="%"
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={!fabricToAdd || fabricMutation.isPending}
            onClick={() => {
              setSectionOk(null)
              fabricMutation.mutate({
                product_id: productId,
                action: 'add',
                component_id: Number(fabricToAdd),
                percentage: Number(fabricPct) || 1,
              })
            }}
          >
            Dodaj
          </button>
        </div>
        {(product.fabric || []).length === 0 ? (
          <div className="empty-state">Brak składu materiałowego.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Komponent</th>
                <th style={{ width: 100 }}>%</th>
                <th style={{ width: 100 }}>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {product.fabric.map((item) => (
                <tr key={item.component_id}>
                  <td>{item.component_name || item.component_id}</td>
                  <td>{item.percentage}%</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-danger-sm"
                      disabled={fabricMutation.isPending}
                      onClick={() => {
                        setSectionOk(null)
                        fabricMutation.mutate({
                          product_id: productId,
                          action: 'remove',
                          component_id: item.component_id,
                        })
                      }}
                    >
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="page-card">
        <h3 className="section-title">Ścieżki</h3>
        <div className="inline-add">
          <input
            className="search-input"
            placeholder="Filtruj ścieżki…"
            value={pathFilter}
            onChange={(e) => setPathFilter(e.target.value)}
          />
        </div>
        {(product.paths || []).length > 0 && (
          <p className="muted-note">
            Przypisane: {(product.paths || []).map((p) => p.name || p.id).join(', ')}
          </p>
        )}
        <div className="paths-list">
          {filteredPaths.slice(0, 200).map((p) => {
            const checked = assignedPathIds.has(p.id)
            return (
              <label key={p.id} className={`path-row ${checked ? 'path-row--on' : ''}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={pathMutation.isPending}
                  onChange={() => {
                    setSectionOk(null)
                    pathMutation.mutate({
                      product_id: productId,
                      path_id: p.id,
                      action: checked ? 'unassign' : 'assign',
                    })
                  }}
                />
                <span>
                  {p.name || '(brak nazwy)'} [{p.path || '-'}] #{p.id}
                </span>
              </label>
            )
          })}
          {(pathsCatalog.data || []).length > 200 && pathFilter.trim() === '' && (
            <p className="muted-note">Pokazano 200 z {(pathsCatalog.data || []).length} — użyj filtra.</p>
          )}
        </div>
      </div>

      <div className="page-card">
        <h3 className="section-title">Powiązane produkty</h3>
        {(product.related_sets || []).length === 0 && (product.series_products || []).length === 0 ? (
          <div className="empty-state">Brak powiązań (zestawy / seria).</div>
        ) : (
          <>
            {(product.related_sets || []).map((set) => (
              <div key={set.id} className="related-block">
                <strong>
                  Zestaw: {set.name} (#{set.id})
                </strong>
                <div className="related-links">
                  {set.products.map((p) => (
                    <Link key={p.id} to={`/products/${p.id}`}>
                      {p.name || `#${p.id}`}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
            {(product.series_products || []).length > 0 && (
              <div className="related-block">
                <strong>Ta sama seria{product.series_name ? ` (${product.series_name})` : ''}</strong>
                <div className="related-links">
                  {product.series_products.map((p) => (
                    <Link key={p.id} to={`/products/${p.id}`}>
                      {p.name || `#${p.id}`}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="page-card">
        <h3 className="section-title">Ceny detaliczne</h3>
        <div className="inline-add">
          <input
            className="search-input"
            style={{ maxWidth: 140 }}
            type="number"
            step="0.01"
            placeholder="Cena dla wszystkich"
            value={bulkRetail}
            onChange={(e) => setBulkRetail(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-muted"
            onClick={() => {
              setRetailDraft((prev) => {
                const next = { ...prev }
                for (const key of Object.keys(next)) {
                  const id = Number(key)
                  next[id] = { ...next[id], retail_price: bulkRetail }
                }
                return next
              })
            }}
          >
            Ustaw dla wszystkich
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={retailMutation.isPending || product.variants.length === 0}
            onClick={() => {
              setSectionOk(null)
              retailMutation.mutate(
                Object.values(retailDraft).map((item) => ({
                  variant_id: item.variant_id,
                  retail_price: item.retail_price,
                  vat_id: item.vat_id ?? item.vat ?? defaultVatId,
                  currency: item.currency || 'PLN',
                })),
              )
            }}
          >
            {retailMutation.isPending ? 'Zapisywanie…' : 'Zapisz ceny'}
          </button>
        </div>
        {product.variants.length === 0 ? (
          <div className="empty-state">Brak wariantów.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Kolor</th>
                <th>Rozmiar</th>
                <th>EAN</th>
                <th>Cena detal.</th>
                <th>VAT</th>
                <th>Waluta</th>
              </tr>
            </thead>
            <tbody>
              {product.variants.map((variant) => {
                const draft = retailDraft[variant.variant_id] || {
                  variant_id: variant.variant_id,
                  retail_price: '',
                  vat: defaultVatId,
                  vat_id: defaultVatId,
                  currency: 'PLN',
                }
                return (
                  <tr key={variant.variant_id}>
                    <td>{variant.color_name || '—'}</td>
                    <td>{variant.size_name || '—'}</td>
                    <td>{variant.ean || '—'}</td>
                    <td>
                      <input
                        className="search-input"
                        style={{ minWidth: 90 }}
                        type="number"
                        step="0.01"
                        value={draft.retail_price ?? ''}
                        onChange={(e) =>
                          setRetailDraft((prev) => ({
                            ...prev,
                            [variant.variant_id]: {
                              ...draft,
                              retail_price: e.target.value,
                            },
                          }))
                        }
                      />
                    </td>
                    <td>
                      <select
                        className="search-input"
                        style={{ minWidth: 110 }}
                        value={String(draft.vat_id ?? draft.vat ?? defaultVatId)}
                        onChange={(e) =>
                          setRetailDraft((prev) => ({
                            ...prev,
                            [variant.variant_id]: {
                              ...draft,
                              vat: Number(e.target.value),
                              vat_id: Number(e.target.value),
                            },
                          }))
                        }
                      >
                        {(vatsCatalog.data || []).map((vat) => (
                          <option key={vat.id} value={vat.id}>
                            {vat.vat_rate != null ? `${vat.vat_rate}%` : `ID ${vat.id}`}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="search-input"
                        style={{ minWidth: 70 }}
                        value={draft.currency ?? 'PLN'}
                        onChange={(e) =>
                          setRetailDraft((prev) => ({
                            ...prev,
                            [variant.variant_id]: {
                              ...draft,
                              currency: e.target.value,
                            },
                          }))
                        }
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
