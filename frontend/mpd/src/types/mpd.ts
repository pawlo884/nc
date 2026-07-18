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
  vat_id?: number | null
  vat_rate?: number | null
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
  ean?: string
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

export interface MpdNamedRef {
  id: number
  name: string | null
}

export interface MpdPathRef {
  id: number
  name: string | null
  path: string | null
  parent_id?: number | null
}

export interface MpdFabricItem {
  component_id: number
  component_name: string | null
  percentage: number
}

export interface MpdRelatedSet {
  id: number
  name: string
  products: MpdNamedRef[]
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
  paths: MpdPathRef[]
  attributes: MpdNamedRef[]
  fabric: MpdFabricItem[]
  related_sets: MpdRelatedSet[]
  series_products: MpdNamedRef[]
  images: MpdProductImage[]
}

export interface MpdProductDetailResponse {
  status: 'success' | 'error'
  message?: string
  product: MpdProductDetail
}

export interface MpdProductUpdatePayload {
  name?: string
  short_description?: string | null
  description?: string | null
  brand_id?: number | null
  collection_id?: number | null
  series_id?: number | null
  season_id?: number | null
  unit_id?: number | null
  visibility?: boolean
}

export interface MpdProductUpdateResponse {
  status: 'success' | 'error'
  message?: string
  product_id?: number
  product_name?: string
}

export interface MpdRetailPriceItem {
  variant_id: number
  retail_price: number | string | null
  vat?: number | string | null
  vat_id?: number | string | null
  currency?: string | null
}

export interface MpdVatOption {
  id: number
  vat_rate: number | null
}

export interface CatalogResponse<T> {
  results: T[]
}

export interface ManageActionResponse {
  status: 'success' | 'error'
  message?: string
}
