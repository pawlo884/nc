import { apiClient } from './client'
import type {
  PaginatedResponse,
  ProductDetailResponse,
  ProductListItem,
  ProductListParams,
} from './types'

export async function fetchProducts(
  params: ProductListParams,
): Promise<PaginatedResponse<ProductListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<ProductListItem>>(
    '/mpd/products/',
    { params },
  )
  return data
}

export async function fetchProduct(
  productId: number,
): Promise<ProductDetailResponse> {
  const { data } = await apiClient.get<ProductDetailResponse>(
    `/mpd/products/${productId}/`,
  )
  return data
}
