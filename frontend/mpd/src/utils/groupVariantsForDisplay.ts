import type { MpdProductVariant } from '../types/mpd';

export type VariantSourceLine = {
  sourceName: string;
  value: string;
};

export type GroupedVariantRow = {
  key: string;
  colorName: string | null;
  hexCode: string | null;
  producerColorName: string | null;
  sizeName: string | null;
  totalStock: number;
  prices: VariantSourceLine[];
  retailPrice: number | null;
  retailCurrency: string | null;
  stockBySource: VariantSourceLine[];
  producerCodes: VariantSourceLine[];
  ean: string;
};

function canonicalEan(variant: MpdProductVariant): string {
  const eans = variant.sources.map(s => s.ean).filter((e): e is string => !!e);
  return [...new Set(eans)].sort().join('|');
}

/**
 * Grupuje warianty jak Django MPD admin (ProductsAdmin.show_variants): ten sam
 * kolor + kolor producenta + rozmiar + zestaw EAN = ten sam wiersz. Stan (suma)
 * i ceny/kody producenta ze wszystkich źródeł wszystkich zgrupowanych wariantów
 * są łączone w jednej komórce (po jednej linii na źródło).
 */
export function groupVariantsForDisplay(variants: MpdProductVariant[]): GroupedVariantRow[] {
  const order: string[] = [];
  const groups = new Map<string, MpdProductVariant[]>();

  for (const variant of variants) {
    const key = [
      variant.color_id ?? '-',
      variant.producer_color_id ?? '-',
      variant.size_id ?? '-',
      canonicalEan(variant),
    ].join('|');
    if (!groups.has(key)) {
      groups.set(key, []);
      order.push(key);
    }
    groups.get(key)!.push(variant);
  }

  return order.map(key => {
    const groupVariants = groups.get(key)!;
    const first = groupVariants[0];

    const totalStock = groupVariants.reduce((sum, v) => sum + (v.stock ?? 0), 0);

    const prices: VariantSourceLine[] = [];
    const stockBySource: VariantSourceLine[] = [];
    const producerCodes: VariantSourceLine[] = [];
    const eans = new Set<string>();

    for (const variant of groupVariants) {
      for (const source of variant.sources) {
        const sourceName = source.source_short_name || source.source_name || `#${source.source_id}`;
        if (source.price != null && source.price > 0) {
          prices.push({ sourceName, value: `${source.price} ${source.currency || 'PLN'}` });
        }
        stockBySource.push({
          sourceName,
          value: source.stock != null ? String(source.stock) : '',
        });
        if (source.producer_code) {
          producerCodes.push({ sourceName, value: source.producer_code });
        }
        if (source.ean) {
          eans.add(source.ean);
        }
      }
    }

    return {
      key,
      colorName: first.color_name,
      hexCode: first.hex_code,
      producerColorName: first.producer_color_name,
      sizeName: first.size_name,
      totalStock,
      prices,
      retailPrice: first.price?.retail_price ?? null,
      retailCurrency: first.price?.currency ?? null,
      stockBySource,
      producerCodes,
      ean: [...eans].sort().join('|'),
    };
  });
}
