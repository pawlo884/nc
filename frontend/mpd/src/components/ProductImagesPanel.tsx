import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { assignImageColor, deleteProductImage, importImagesFromSources } from '../api/mpd';
import { useActionMessages } from '../hooks/useActionMessages';
import type { MpdProductDetail, MpdProductImage } from '../types/mpd';
import { groupImagesByColor } from '../utils/groupImagesByColor';

const FALLBACK_IMG =
  'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5icmFrIHpkajwvdGV4dD48L3N2Zz4=';

const DND_TYPE = 'application/x-mpd-image-id';

function ImageCard({ img, productLabel }: { img: MpdProductImage; productLabel: string }) {
  return (
    <div
      className="mpd-img-card"
      draggable
      onDragStart={e => {
        e.dataTransfer.setData(DND_TYPE, String(img.id));
        e.dataTransfer.effectAllowed = 'move';
      }}
      title={img.source_name ? `źródło: ${img.source_name}` : undefined}
    >
      <img
        src={img.image_url || FALLBACK_IMG}
        alt={productLabel}
        loading="lazy"
        decoding="async"
        width={110}
        height={110}
        onError={e => {
          const el = e.currentTarget;
          el.onerror = null;
          el.src = FALLBACK_IMG;
        }}
      />
      {img.source_name && <span className="mpd-img-card__badge">{img.source_name}</span>}
    </div>
  );
}

export function ProductImagesPanel({
  productId,
  product,
}: {
  productId: number;
  product: MpdProductDetail;
}) {
  const queryClient = useQueryClient();
  const { setError, setSuccess, reportError } = useActionMessages();
  const [dragOver, setDragOver] = useState<string | null>(null);

  const { groups, slots, tray } = useMemo(
    () => groupImagesByColor(product.images ?? [], product.variants ?? []),
    [product.images, product.variants]
  );

  const groupsBySlot = useMemo(() => {
    const m = new Map(groups.map(g => [g.colorId, g]));
    return m;
  }, [groups]);

  function invalidate() {
    return queryClient.invalidateQueries({ queryKey: ['mpd-product', productId] });
  }

  const importMutation = useMutation({
    mutationFn: () => importImagesFromSources(productId),
    onSuccess: async res => {
      if (res.status === 'error') {
        setError(res.message || 'Import zdjęć nieudany.');
        return;
      }
      setSuccess(
        `Zaimportowano ${res.imported ?? 0}, pominięto ${res.skipped ?? 0}.` +
          (res.errors && res.errors.length ? ` Błędy: ${res.errors.length}.` : '')
      );
      await invalidate();
    },
    onError: err => reportError(err, 'Import zdjęć nieudany.'),
  });

  const assignMutation = useMutation({
    mutationFn: (vars: { imageId: number; colorId: number | null }) =>
      assignImageColor(productId, vars.imageId, vars.colorId),
    onSuccess: async res => {
      if (res.status === 'error') {
        setError(res.message || 'Nie udało się przenieść zdjęcia.');
        return;
      }
      await invalidate();
    },
    onError: err => reportError(err, 'Nie udało się przenieść zdjęcia.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (imageId: number) => deleteProductImage(productId, imageId),
    onSuccess: async res => {
      if (res.status === 'error') {
        setError(res.message || 'Nie udało się usunąć zdjęcia.');
        return;
      }
      setSuccess('Zdjęcie usunięte.');
      await invalidate();
    },
    onError: err => reportError(err, 'Nie udało się usunąć zdjęcia.'),
  });

  const busy = assignMutation.isPending || deleteMutation.isPending || importMutation.isPending;
  const productLabel = product.name || `produkt ${productId}`;

  function readId(e: React.DragEvent): number | null {
    const raw = e.dataTransfer.getData(DND_TYPE);
    const id = Number(raw);
    return Number.isFinite(id) && id > 0 ? id : null;
  }

  function dropHandlers(zoneKey: string, onDrop: (imageId: number) => void) {
    return {
      onDragOver: (e: React.DragEvent) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOver !== zoneKey) setDragOver(zoneKey);
      },
      onDragLeave: () => setDragOver(prev => (prev === zoneKey ? null : prev)),
      onDrop: (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(null);
        const id = readId(e);
        if (id != null) onDrop(id);
      },
    };
  }

  const totalImages = product.images?.length ?? 0;

  return (
    <div className="page-card product-detail__images">
      <h3 className="section-title">
        Zdjęcia
        <span className="section-count">{totalImages}</span>
        <button
          type="button"
          className="btn btn-muted"
          style={{ marginLeft: 'auto' }}
          disabled={busy}
          onClick={() => importMutation.mutate()}
        >
          {importMutation.isPending ? 'Pobieranie…' : 'Pobierz zdjęcia z hurtowni'}
        </button>
      </h3>

      {/* Tacka */}
      <div
        className={`mpd-img-zone mpd-img-zone--tray ${dragOver === 'tray' ? 'is-over' : ''}`}
        {...dropHandlers('tray', id => assignMutation.mutate({ imageId: id, colorId: null }))}
      >
        <div className="mpd-img-zone__head">
          Do przypisania
          <span className="section-count">{tray.length}</span>
        </div>
        {tray.length === 0 ? (
          <p className="muted-note">
            Przeciągnij tutaj zdjęcie, którego nie chcesz przypisywać do koloru.
          </p>
        ) : (
          <div className="mpd-img-grid">
            {tray.map(img => (
              <ImageCard key={img.id} img={img} productLabel={productLabel} />
            ))}
          </div>
        )}
      </div>

      {/* Kolory */}
      <div className="mpd-img-slots">
        {slots.length === 0 && (
          <p className="empty-state">Produkt nie ma kolorów (wariantów) — brak stref.</p>
        )}
        {slots.map(slot => {
          const g = groupsBySlot.get(slot.colorId);
          const imgs = g?.images ?? [];
          const zoneKey = `slot-${slot.colorId}`;
          return (
            <div
              key={slot.colorId}
              className={`mpd-img-zone ${dragOver === zoneKey ? 'is-over' : ''}`}
              {...dropHandlers(zoneKey, id =>
                assignMutation.mutate({ imageId: id, colorId: slot.colorId })
              )}
            >
              <div className="mpd-img-zone__head">
                {slot.label}
                {slot.kind === 'producer' && (
                  <span className="image-group__badge">kolor producenta</span>
                )}
                <span className="section-count">{imgs.length}</span>
              </div>
              {imgs.length === 0 ? (
                <p className="muted-note">Przeciągnij zdjęcia tego koloru tutaj.</p>
              ) : (
                <div className="mpd-img-grid">
                  {imgs.map(img => (
                    <ImageCard key={img.id} img={img} productLabel={productLabel} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Kosz */}
      <div
        className={`mpd-img-zone mpd-img-zone--trash ${dragOver === 'trash' ? 'is-over' : ''}`}
        {...dropHandlers('trash', id => {
          if (window.confirm('Usunąć to zdjęcie na stałe?')) {
            deleteMutation.mutate(id);
          }
        })}
      >
        🗑 Kosz — przeciągnij zdjęcie tutaj, żeby usunąć na stałe
      </div>
    </div>
  );
}
