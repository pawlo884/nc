export interface ProductListItem {
  id: number
  name: string
  brand_name: string | null
  visibility: boolean
  created_at: string | null
  updated_at: string | null
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface VariantPrice {
  retail_price: number | null
  vat: number | null
  currency: string | null
  net_price: number | null
}

export interface ProductVariant {
  variant_id: number
  color_id: number | null
  producer_color_id: number | null
  size_id: number | null
  producer_code: string
  exported_to_iai: boolean
  price: VariantPrice | null
}

export interface ProductDetail {
  id: number
  name: string
  description: string | null
  short_description: string | null
  brand_id: number | null
  unit_id: number | null
  series_id: number | null
  visibility: boolean
  created_at: string | null
  updated_at: string | null
  variants: ProductVariant[]
  paths: number[]
  attributes: number[]
}

export interface ProductDetailResponse {
  status: 'success' | 'error'
  product: ProductDetail
}

export interface ProductListParams {
  page?: number
  page_size?: number
  search?: string
  brand_id?: number
  visibility?: boolean
}
