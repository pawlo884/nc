const PLACEHOLDER_56 =
  'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTYiIGhlaWdodD0iNTYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+YnJhayB6ZGo8L3RleHQ+PC9zdmc+';

type ProductThumbnailProps = {
  src: string | null | undefined;
  alt?: string;
  size?: number;
};

export function ProductThumbnail({
  src,
  alt = 'Obraz produktu',
  size = 56,
}: ProductThumbnailProps) {
  if (!src) {
    return <span className="product-thumb product-thumb--empty">—</span>;
  }

  return (
    <img
      className="product-thumb"
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      width={size}
      height={size}
      onError={e => {
        const img = e.currentTarget;
        img.onerror = null;
        img.src = PLACEHOLDER_56;
      }}
    />
  );
}
