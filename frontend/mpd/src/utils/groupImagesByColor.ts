import type { MpdProductImage, MpdProductVariant } from '../types/mpd';

export type ImageColorSlot = {
  /** producer_color_id / color_id — cel drag&drop */
  colorId: number;
  label: string;
  kind: 'producer' | 'color';
};

export type ImageColorGroup = ImageColorSlot & {
  key: string;
  images: MpdProductImage[];
};

export type GroupedImages = {
  /** grupy z co najmniej jednym zdjęciem */
  groups: ImageColorGroup[];
  /** wszystkie kolory produktu (także puste) — strefy upuszczania */
  slots: ImageColorSlot[];
  /** zdjęcia bez przypisanego koloru — „tacka" */
  tray: MpdProductImage[];
};

function normalizeColorKey(name: string): string {
  return name.toLowerCase().replace(/\//g, '_').replace(/ /g, '_');
}

function basenameLower(filePath: string): string {
  const parts = filePath.replace(/\\/g, '/').split('/');
  return (parts[parts.length - 1] || filePath).toLowerCase();
}

/**
 * Grupuje zdjęcia po kolorze:
 * 1. jeśli zdjęcie ma producer_color_id → do tego koloru,
 * 2. inaczej heurystyka po nazwie pliku (jak Django MPD admin — kolor producenta,
 *    potem zwykły kolor, dłuższe nazwy pierwsze),
 * 3. inaczej → tacka (do ręcznego przypisania drag&drop).
 */
export function groupImagesByColor(
  images: MpdProductImage[],
  variants: MpdProductVariant[]
): GroupedImages {
  const producerMap = new Map<number, string>();
  const colorMap = new Map<number, string>();

  for (const v of variants) {
    if (v.producer_color_id != null && v.producer_color_name) {
      producerMap.set(v.producer_color_id, v.producer_color_name);
    }
    if (v.color_id != null && v.color_name) {
      colorMap.set(v.color_id, v.color_name);
    }
  }

  // Sloty: najpierw kolory producenta, potem zwykłe (bez duplikatów id).
  const slots: ImageColorSlot[] = [];
  const slotIds = new Set<number>();
  for (const [id, label] of producerMap) {
    slots.push({ colorId: id, label, kind: 'producer' });
    slotIds.add(id);
  }
  for (const [id, label] of colorMap) {
    if (!slotIds.has(id)) {
      slots.push({ colorId: id, label, kind: 'color' });
      slotIds.add(id);
    }
  }

  const producerKeys = [...producerMap.entries()]
    .map(([id, name]) => ({ id, key: normalizeColorKey(name) }))
    .sort((a, b) => b.key.length - a.key.length);
  const colorKeys = [...colorMap.entries()]
    .map(([id, name]) => ({ id, key: normalizeColorKey(name) }))
    .sort((a, b) => b.key.length - a.key.length);

  const bySlot = new Map<number, MpdProductImage[]>(slots.map(s => [s.colorId, []]));
  const tray: MpdProductImage[] = [];

  for (const img of images) {
    let slotId: number | null = null;

    if (img.producer_color_id != null && bySlot.has(img.producer_color_id)) {
      slotId = img.producer_color_id;
    } else if (img.producer_color_id == null) {
      const fileName = basenameLower(img.file_path);
      for (const { id, key } of producerKeys) {
        if (key && fileName.includes(key)) {
          slotId = id;
          break;
        }
      }
      if (slotId == null) {
        for (const { id, key } of colorKeys) {
          if (key && fileName.includes(key)) {
            slotId = id;
            break;
          }
        }
      }
    }

    if (slotId != null) {
      bySlot.get(slotId)!.push(img);
    } else {
      tray.push(img);
    }
  }

  const groups: ImageColorGroup[] = slots
    .map(s => ({ ...s, key: `color-${s.colorId}`, images: bySlot.get(s.colorId) ?? [] }))
    .filter(g => g.images.length > 0);

  return { groups, slots, tray };
}
