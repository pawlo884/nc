import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { attachOrphanVariant, fetchOrphanVariants } from '../api/mpd';
import { useActionMessages } from '../hooks/useActionMessages';
import type { MpdOrphanVariant, MpdProductDetail, MpdProductVariant } from '../types/mpd';

type RowKey = string;
type ColorOption = { id: number; name: string };

function rowKey(o: MpdOrphanVariant): RowKey {
  return `${o.source_id}:${o.variant_uid}:${o.ean}`;
}

/** Unikalne kolory / kolory producenta z wariantów tego produktu. */
function colorOptionsFromVariants(
  variants: MpdProductVariant[],
  which: 'color' | 'producer'
): ColorOption[] {
  const map = new Map<number, string>();
  for (const v of variants) {
    const id = which === 'color' ? v.color_id : v.producer_color_id;
    const name = which === 'color' ? v.color_name : v.producer_color_name;
    if (id != null && !map.has(id)) map.set(id, name || `#${id}`);
  }
  return [...map.entries()].map(([id, name]) => ({ id, name }));
}

interface DraftState {
  mode: 'existing' | 'new';
  targetVariantId: string;
  colorId: string;
  producerColorId: string;
  sizeName: string;
}

function emptyDraft(
  o: MpdOrphanVariant,
  colors: ColorOption[],
  variants: MpdProductVariant[]
): DraftState {
  // dopasuj kolor hurtowni (o.color) do koloru produktu po nazwie, inaczej pierwszy
  const wanted = (o.color || '').trim().toLowerCase();
  const matched =
    colors.find(c => c.name.toLowerCase() === wanted) ??
    (colors.length === 1 ? colors[0] : undefined);
  // kolor producenta: taki jak w innych wariantach tego koloru
  const sibling = matched
    ? variants.find(v => v.color_id === matched.id && v.producer_color_id != null)
    : undefined;
  return {
    mode: 'existing',
    targetVariantId: '',
    colorId: matched ? String(matched.id) : '',
    producerColorId: sibling?.producer_color_id != null ? String(sibling.producer_color_id) : '',
    sizeName: o.size || '',
  };
}

export function OrphanVariantsPanel({
  productId,
  product,
}: {
  productId: number;
  product: MpdProductDetail;
}) {
  const queryClient = useQueryClient();
  const { setError, setSuccess, reportError } = useActionMessages();
  const [openRow, setOpenRow] = useState<RowKey | null>(null);
  const [drafts, setDrafts] = useState<Record<RowKey, DraftState>>({});

  const colorOptions = useMemo(
    () => colorOptionsFromVariants(product.variants, 'color'),
    [product.variants]
  );
  const producerColorOptions = useMemo(
    () => colorOptionsFromVariants(product.variants, 'producer'),
    [product.variants]
  );

  const { data, isLoading } = useQuery({
    queryKey: ['mpd-orphan-variants', productId],
    queryFn: () => fetchOrphanVariants(productId),
    enabled: Number.isFinite(productId) && productId > 0,
  });

  const mutation = useMutation({
    mutationFn: (vars: { o: MpdOrphanVariant; draft: DraftState }) => {
      const { o, draft } = vars;
      return attachOrphanVariant(productId, {
        source_id: o.source_id,
        source_variant_uid: o.variant_uid,
        source_product_id: o.source_product_id,
        ean: o.ean,
        producer_code: o.producer_code || undefined,
        stock: o.stock,
        price: o.price,
        currency: o.currency,
        mode: draft.mode,
        target_variant_id: draft.mode === 'existing' ? Number(draft.targetVariantId) : undefined,
        color_id: draft.mode === 'new' ? Number(draft.colorId) : undefined,
        producer_color_id:
          draft.mode === 'new' && draft.producerColorId ? Number(draft.producerColorId) : undefined,
        size_name: draft.mode === 'new' ? draft.sizeName || undefined : undefined,
      });
    },
    onSuccess: async res => {
      if (res.status === 'error') {
        setError(res.message || 'Nie udało się przypiąć wariantu.');
        return;
      }
      setSuccess(res.message || 'Wariant przypięty.');
      setOpenRow(null);
      await queryClient.invalidateQueries({ queryKey: ['mpd-orphan-variants', productId] });
      await queryClient.invalidateQueries({ queryKey: ['mpd-product', productId] });
    },
    onError: err => reportError(err, 'Nie udało się przypiąć wariantu.'),
  });

  const rows = data?.results ?? [];

  return (
    <div className="page-card product-detail__wide">
      <h3 className="section-title">
        Warianty nieprzypisane (orphaned)
        <span className="section-count">{rows.length}</span>
      </h3>
      <p className="muted-note">
        Warianty z hurtowni, których produkt jest zmapowany do tego produktu MPD, ale sam wariant
        nie został jeszcze dopięty po EAN (np. inny kolor pod jednym produktem hurtowni albo
        rozjechany EAN). Przypnij je do istniejącego wariantu MPD lub utwórz nowy.
      </p>

      {isLoading ? (
        <div className="loading">Ładowanie…</div>
      ) : rows.length === 0 ? (
        <div className="empty-state">Brak nieprzypisanych wariantów.</div>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Źródło</th>
                <th>Kolor (hurtownia)</th>
                <th>Rozmiar</th>
                <th>EAN</th>
                <th style={{ width: 70 }}>Stan</th>
                <th style={{ width: 90 }}>Cena</th>
                <th style={{ width: 220 }}>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(o => {
                const key = rowKey(o);
                const draft = drafts[key] || emptyDraft(o, colorOptions, product.variants);
                const isOpen = openRow === key;
                const setDraft = (patch: Partial<DraftState>) =>
                  setDrafts(prev => ({ ...prev, [key]: { ...draft, ...patch } }));
                return (
                  <tr key={key}>
                    <td>{o.source_name || o.source_id}</td>
                    <td>{o.color || <span className="muted">—</span>}</td>
                    <td>{o.size || <span className="muted">—</span>}</td>
                    <td>{o.ean || <span className="muted">—</span>}</td>
                    <td>{o.stock ?? <span className="muted">—</span>}</td>
                    <td>
                      {o.price != null ? (
                        `${o.price} ${o.currency}`
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {!isOpen ? (
                        <button
                          type="button"
                          className="btn btn-muted"
                          onClick={() => {
                            setDrafts(prev => ({
                              ...prev,
                              [key]: emptyDraft(o, colorOptions, product.variants),
                            }));
                            setOpenRow(key);
                          }}
                        >
                          Przypnij
                        </button>
                      ) : (
                        <div className="orphan-attach">
                          <select
                            className="search-input"
                            value={draft.mode}
                            onChange={e => setDraft({ mode: e.target.value as 'existing' | 'new' })}
                          >
                            <option value="existing">Do istniejącego wariantu</option>
                            <option value="new">Utwórz nowy wariant</option>
                          </select>

                          {draft.mode === 'existing' ? (
                            <select
                              className="search-input"
                              value={draft.targetVariantId}
                              onChange={e => setDraft({ targetVariantId: e.target.value })}
                            >
                              <option value="">Wybierz wariant…</option>
                              {product.variants.map(v => (
                                <option key={v.variant_id} value={v.variant_id}>
                                  {(v.color_name || '—') + ' / ' + (v.size_name || '—')}
                                  {v.ean ? ` (${v.ean})` : ''}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <>
                              <select
                                className="search-input"
                                value={draft.colorId}
                                onChange={e => setDraft({ colorId: e.target.value })}
                              >
                                <option value="">Kolor…</option>
                                {colorOptions.map(c => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                              <select
                                className="search-input"
                                value={draft.producerColorId}
                                onChange={e => setDraft({ producerColorId: e.target.value })}
                              >
                                <option value="">Kolor producenta (opc.)…</option>
                                {producerColorOptions.map(c => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                              <input
                                className="search-input"
                                placeholder="rozmiar"
                                value={draft.sizeName}
                                onChange={e => setDraft({ sizeName: e.target.value })}
                              />
                            </>
                          )}

                          <div className="orphan-attach__actions">
                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={
                                mutation.isPending ||
                                (draft.mode === 'existing' && !draft.targetVariantId) ||
                                (draft.mode === 'new' && !draft.colorId)
                              }
                              onClick={() => mutation.mutate({ o, draft })}
                            >
                              {mutation.isPending ? 'Przypinanie…' : 'Zatwierdź'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-muted"
                              onClick={() => setOpenRow(null)}
                            >
                              Anuluj
                            </button>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
