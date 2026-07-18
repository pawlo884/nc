import { apiClient } from './client'
import type {
  AuthResponse,
  CatalogResponse,
  ManageActionResponse,
  MpdFabricItem,
  MpdNamedRef,
  MpdPathRef,
  MpdProduct,
  MpdProductDetailResponse,
  MpdProductUpdatePayload,
  MpdProductUpdateResponse,
  MpdRetailPriceItem,
  MpdVatOption,
  PaginatedResponse,
} from '../types/mpd'

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/api/auth/token/', {
    username,
    password,
  })
  return data
}

export async function fetchProducts(params: {
  search?: string
  brand_id?: number
  visibility?: boolean
  page?: number
  page_size?: number
}): Promise<PaginatedResponse<MpdProduct>> {
  const { data } = await apiClient.get<PaginatedResponse<MpdProduct>>('/api/mpd/products/', {
    params,
  })
  return data
}

export async function fetchProduct(productId: number): Promise<MpdProductDetailResponse> {
  const { data } = await apiClient.get<MpdProductDetailResponse>(
    `/api/mpd/products/${productId}/`,
  )
  return data
}

export async function updateProduct(
  productId: number,
  payload: MpdProductUpdatePayload,
): Promise<MpdProductUpdateResponse> {
  const { data } = await apiClient.patch<MpdProductUpdateResponse>(
    `/api/mpd/products/${productId}/`,
    payload,
  )
  return data
}

export async function fetchCatalogAttributes(): Promise<MpdNamedRef[]> {
  const { data } = await apiClient.get<CatalogResponse<MpdNamedRef>>('/api/mpd/catalog/attributes/')
  return data.results
}

export async function fetchCatalogFabricComponents(): Promise<MpdNamedRef[]> {
  const { data } = await apiClient.get<CatalogResponse<MpdNamedRef>>(
    '/api/mpd/catalog/fabric-components/',
  )
  return data.results
}

export async function fetchCatalogPaths(): Promise<MpdPathRef[]> {
  const { data } = await apiClient.get<CatalogResponse<MpdPathRef>>('/api/mpd/catalog/paths/')
  return data.results
}

export async function fetchCatalogVats(): Promise<MpdVatOption[]> {
  const { data } = await apiClient.get<CatalogResponse<MpdVatOption>>('/api/mpd/catalog/vats/')
  return data.results
}

export async function manageProductAttributes(payload: {
  product_id: number
  action: 'add' | 'remove'
  attribute_ids?: number[]
  attribute_id?: number
}): Promise<ManageActionResponse> {
  const { data } = await apiClient.post<ManageActionResponse>(
    '/api/mpd/products/manage-attributes/',
    payload,
  )
  return data
}

export async function manageProductFabric(payload: {
  product_id: number
  action: 'add' | 'remove'
  component_id: number
  percentage?: number
}): Promise<ManageActionResponse> {
  const { data } = await apiClient.post<ManageActionResponse>(
    '/api/mpd/products/manage-fabric/',
    payload,
  )
  return data
}

export async function manageProductPaths(payload: {
  product_id: number
  path_id: number
  action: 'assign' | 'unassign'
}): Promise<ManageActionResponse> {
  const { data } = await apiClient.post<ManageActionResponse>(
    '/api/mpd/products/manage-paths/',
    payload,
  )
  return data
}

export async function updateRetailPrices(
  productId: number,
  prices: MpdRetailPriceItem[],
): Promise<ManageActionResponse> {
  const { data } = await apiClient.post<ManageActionResponse>(
    `/api/mpd/products/${productId}/retail-prices/`,
    { prices },
  )
  return data
}

export type { MpdFabricItem }
