export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface MpdProduct {
  id: number
  name: string
  brand_name: string | null
  visibility: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  token: string
  user_id: number
  username: string
  is_staff: boolean
}

export interface MpdVariantPrice {
  retail_price: number | null
  vat: number | null
  currency: string | null
  net_price: number | null
}

export interface MpdProductVariant {
  variant_id: number
  color_id: number | null
  color_name: string | null
  hex_code: string | null
  producer_color_id: number | null
  producer_color_name: string | null
  size_id: number | null
  size_name: string | null
  producer_code: string
  exported_to_iai: boolean
  stock: number | null
  warehouse_price: number | null
  price: MpdVariantPrice | null
}

export interface MpdProductImage {
  id: number
  image_url: string | null
  file_path: string
}

export interface MpdProductDetail {
  id: number
  name: string
  description: string | null
  short_description: string | null
  brand_id: number | null
  brand_name: string | null
  collection_id: number | null
  collection_name: string | null
  series_id: number | null
  series_name: string | null
  season_id: number | null
  season_name: string | null
  unit_id: number | null
  unit_name: string | null
  visibility: boolean
  created_at: string | null
  updated_at: string | null
  variants: MpdProductVariant[]
  paths: number[]
  attributes: number[]
  images: MpdProductImage[]
}

export interface MpdProductDetailResponse {
  status: 'success' | 'error'
  message?: string
  product: MpdProductDetail
}
