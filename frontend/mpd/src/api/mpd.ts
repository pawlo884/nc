import { apiClient } from './client'
import type {
  AuthResponse,
  MpdProduct,
  MpdProductDetailResponse,
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
