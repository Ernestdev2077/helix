import axios, { type AxiosInstance } from 'axios'

import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'

const baseURL = import.meta.env.VITE_API_URL || ''

export const api: AxiosInstance = axios.create({
  baseURL: `${baseURL}/api/v1`,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
})

/**
 * Unwrap a DRF-paginated response of the shape `{count, results: T[]}` to
 * a flat array. Pass-through for already-flat responses.
 */
export function unwrapList<T>(data: T[] | { results: T[] } | undefined | null): T[] {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (typeof data === 'object' && Array.isArray((data as { results?: T[] }).results)) {
    return (data as { results: T[] }).results
  }
  return []
}

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  const workspaces = useWorkspaceStore()
  if (workspaces.activeWorkspaceId) {
    config.headers['X-Workspace'] = workspaces.activeWorkspaceId
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      await auth.clear()
    }
    return Promise.reject(error)
  },
)
