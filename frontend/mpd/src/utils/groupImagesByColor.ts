import type { MpdProductImage, MpdProductVariant } from '../types/mpd';

export type ImageColorGroup = {
  key: string;
  label: string;
  kind: 'producer' | 'color' | 'other';
  images: MpdProductImage[];
};

function normalizeColorKey(name: string): string {
  return name.toLowerCase().replace(/\//g, '_').replace(/ /g, '_');
}

function basenameLower(filePath: string): string {
  const parts = filePath.replace(/\\/g, '/').split('/');
  return (parts[parts.length - 1] || filePath).toLowerCase();
}

/**
 * Grupuje zdjęcia jak Django MPD admin: match nazwy koloru w basename file_path
 * (najpierw kolor producenta, potem zwykły kolor; dłuższe nazwy pierwsze).
 */
export function groupImagesByColor(
  images: MpdProductImage[],
  variants: MpdProductVariant[],
): ImageColorGroup[] {
  const producerMap = new Map<string, string>();
  const colorMap = new Map<string, string>();

  for (const v of variants) {
    if (v.producer_color_id != null && v.producer_color_name) {
      producerMap.set(String(v.producer_color_id), v.producer_color_name);
    }
    if (v.color_id != null && v.color_name) {
      colorMap.set(String(v.color_id), v.color_name);
    }
  }

  const producerKeys = [...producerMap.entries()]
    .map(([id, name]) => ({ id, name, key: normalizeColorKey(name) }))
    .sort((a, b) => b.key.length - a.key.length);

  const colorKeys = [...colorMap.entries()]
    .map(([id, name]) => ({ id, name, key: normalizeColorKey(name) }))
    .sort((a, b) => b.key.length - a.key.length);

  const byProducer = new Map<string, MpdProductImage[]>(
    [...producerMap.keys()].map(id => [id, []]),
  );
  const byColor = new Map<string, MpdProductImage[]>(
    [...colorMap.keys()].map(id => [id, []]),
  );
  const other: MpdProductImage[] = [];

  for (const img of images) {
    const fileName = basenameLower(img.file_path);
    let matched = false;

    for (const { id, key } of producerKeys) {
      if (key && fileName.includes(key)) {
        byProducer.get(id)?.push(img);
        matched = true;
        break;
      }
    }

    if (!matched) {
      for (const { id, key } of colorKeys) {
        if (key && fileName.includes(key)) {
          byColor.get(id)?.push(img);
          matched = true;
          break;
        }
      }
    }

    if (!matched) {
      other.push(img);
    }
  }

  const groups: ImageColorGroup[] = [];

  for (const [id, name] of producerMap) {
    const imgs = byProducer.get(id) ?? [];
    if (imgs.length > 0) {
      groups.push({
        key: `producer-${id}`,
        label: name,
        kind: 'producer',
        images: imgs,
      });
    }
  }

  for (const [id, name] of colorMap) {
    const imgs = byColor.get(id) ?? [];
    if (imgs.length > 0) {
      groups.push({
        key: `color-${id}`,
        label: name,
        kind: 'color',
        images: imgs,
      });
    }
  }

  if (other.length > 0) {
    groups.push({
      key: 'other',
      label: 'Inne zdjęcia',
      kind: 'other',
      images: other,
    });
  }

  return groups;
}
