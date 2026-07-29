import { Link } from 'react-router';
import type { MpdProduct } from '../types/mpd';
import { ProductThumbnail } from './ProductThumbnail';

interface ProductCardProps {
  product: MpdProduct;
  onDelete: (productId: number, productName: string) => void;
  deleteDisabled: boolean;
}

export function ProductCard({ product, onDelete, deleteDisabled }: ProductCardProps) {
  return (
    <Link to={`/products/${product.id}`} className="product-card">
      <div className="product-card__image">
        <ProductThumbnail
          src={product.thumbnail_url}
          alt={product.name || `Produkt ${product.id}`}
          size={160}
        />
      </div>
      <div className="product-card__body">
        <p className="product-card__name">{product.name}</p>
        <p className="product-card__brand">{product.brand_name || '—'}</p>
        <div className="product-card__meta">
          <span className={`badge ${product.visibility ? 'badge-visible' : 'badge-hidden'}`}>
            {product.visibility ? 'Widoczny' : 'Ukryty'}
          </span>
          <span className="product-card__id">#{product.id}</span>
        </div>
      </div>
      <button
        type="button"
        className="btn btn-danger-sm product-card__delete"
        disabled={deleteDisabled}
        onClick={e => {
          e.preventDefault();
          e.stopPropagation();
          onDelete(product.id, product.name);
        }}
      >
        Usuń
      </button>
    </Link>
  );
}
