import { api, unwrapList } from './client'

// ----------------------------- Types -----------------------------

export type Platform = 'x' | 'reddit' | 'linkedin'

export interface Workspace {
  id: string
  name: string
  slug: string
  plan: string
  my_role: string | null
  ai_credits_monthly: number
  ai_credits_used: number
}

export interface Brand {
  id: string
  name: string
  slug: string
  description: string
  voice_description: string
  voice_do: string[]
  voice_dont: string[]
  target_audience: string
  accent_color: string
}

export interface VariantMedia {
  asset_id: string
  type: 'image' | 'video' | 'gif'
  url: string
  alt: string
  width?: number
  height?: number
  source?: 'upload' | 'ai' | 'url'
}

export interface PostVariant {
  id: string
  post: string
  platform: Platform
  label: string
  content: string
  hook_strategy: string
  media: VariantMedia[]
  status: string
  is_starred: boolean
  critic_notes: { severity: string; message: string; fix_suggestion?: string }[]
  allocation_weight: number
  created_at: string
}

export interface MediaAsset {
  id: string
  url: string
  source: 'upload' | 'ai' | 'url'
  mime_type: string
  width: number
  height: number
  size_bytes: number
  alt_text: string
  ai_prompt: string
  ai_model: string
  cost_usd: string | number
  created_at: string
}

export interface Post {
  id: string
  brand: string
  campaign: string | null
  brief: string
  goals: string[]
  tone_hints: string[]
  target_platforms: Platform[]
  status: string
  variants: PostVariant[]
  pinned_reference_ids: string[]
  created_at: string
}

export interface ReferenceDNA {
  tone?: string
  structure?: string
  hook_patterns?: string
  style_rules?: string[]
  key_phrases?: string[]
}

export interface Reference {
  id: string
  brand: string
  platform: Platform
  source: string
  source_url: string
  raw_text: string
  tags: string[]
  source_metrics: Record<string, unknown>
  extracted_features: ReferenceDNA
  likes_count: number
  use_count: number
  created_at: string
}

export interface StyleRule {
  id: string
  brand: string
  scope: 'global' | 'platform' | 'campaign'
  platform: string
  rule_text: string
  rationale: string
  confidence: number
  status: 'proposed' | 'approved' | 'rejected' | 'paused'
  version: number
  created_at: string
}

export interface AgentRun {
  id: string
  kind: string
  status: string
  post: string | null
  started_at: string | null
  finished_at: string | null
  total_tokens_in: number
  total_tokens_out: number
  total_cost_usd: string
  created_at: string
}

// ----------------------------- Endpoints -----------------------------

type Paginated<T> = T[] | { results: T[] }

export const workspacesApi = {
  list: () => api.get<Paginated<Workspace>>('/workspaces/').then((r) => unwrapList(r.data)),
  create: (data: { name: string }) =>
    api.post<Workspace>('/workspaces/', data).then((r) => r.data),
}

export const brandsApi = {
  list: () => api.get<Paginated<Brand>>('/brands/').then((r) => unwrapList(r.data)),
  create: (data: Partial<Brand>) => api.post<Brand>('/brands/', data).then((r) => r.data),
  update: (id: string, data: Partial<Brand>) =>
    api.patch<Brand>(`/brands/${id}/`, data).then((r) => r.data),
}

export const postsApi = {
  list: () => api.get<Paginated<Post>>('/content/posts/').then((r) => unwrapList(r.data)),
  create: (data: Partial<Post>) =>
    api.post<Post>('/content/posts/', data).then((r) => r.data),
  get: (id: string) => api.get<Post>(`/content/posts/${id}/`).then((r) => r.data),
  generate: (id: string) =>
    api.post<{ agent_run_id: string; post_id: string }>(`/content/posts/${id}/generate/`).then(
      (r) => r.data,
    ),
}

export const variantsApi = {
  star: (id: string) =>
    api.post<PostVariant>(`/content/variants/${id}/star/`).then((r) => r.data),
  unstar: (id: string) =>
    api.post<PostVariant>(`/content/variants/${id}/unstar/`).then((r) => r.data),
  refine: (id: string) =>
    api
      .post<{ agent_run_id: string; post_id: string; source_variant_id: string }>(
        `/content/variants/${id}/refine/`,
      )
      .then((r) => r.data),
  attachImage: (id: string, assetId: string) =>
    api
      .post<{ variant: PostVariant; asset: MediaAsset }>(
        `/content/variants/${id}/attach-image/`,
        { asset_id: assetId },
      )
      .then((r) => r.data),
  detachImage: (id: string) =>
    api.post<PostVariant>(`/content/variants/${id}/detach-image/`).then((r) => r.data),
  generateImage: (id: string) =>
    api
      .post<{ variant: PostVariant; asset: MediaAsset }>(
        `/content/variants/${id}/generate-image/`,
      )
      .then((r) => r.data),
}

export interface PlatformOAuthStatus {
  configured: boolean
  connected: boolean
  handle: string
  display_name: string
}

export interface OAuthStatus {
  x: PlatformOAuthStatus
  reddit: PlatformOAuthStatus
  linkedin: PlatformOAuthStatus
}

export const oauthApi = {
  status: () => api.get<OAuthStatus>('/publishing/oauth-status/').then((r) => r.data),
}

export interface KBDocument {
  id: string
  brand: string
  title: string
  source_type: string
  source_uri: string
  status: string
  error_message: string
  token_count: number
  created_at: string
  chunk_count?: number
}

export const kbDocumentsApi = {
  list: (params?: { brand?: string }) =>
    api
      .get<Paginated<KBDocument>>('/brands/documents/', { params })
      .then((r) => unwrapList(r.data)),
  paste: (data: { brand: string; title: string; raw_text: string }) =>
    api.post<KBDocument>('/brands/documents/paste/', data).then((r) => r.data),
}

export const mediaApi = {
  upload: (file: File, brandId?: string, altText?: string) => {
    const fd = new FormData()
    fd.append('file', file)
    if (brandId) fd.append('brand', brandId)
    if (altText) fd.append('alt_text', altText)
    return api
      .post<MediaAsset>('/media/upload/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
}

export const brandsCurateApi = {
  curate: (brandId: string) =>
    api.post<{ agent_run_id: string; brand_id: string }>(`/brands/${brandId}/curate/`).then(
      (r) => r.data,
    ),
}

export const referencesApi = {
  list: (params?: { platform?: Platform; brand?: string }) =>
    api
      .get<Paginated<Reference>>('/content/references/', { params })
      .then((r) => unwrapList(r.data)),
  create: (data: Partial<Reference>) =>
    api.post<Reference>('/content/references/', data).then((r) => r.data),
  remove: (id: string) => api.delete(`/content/references/${id}/`),
  extractDna: (id: string) =>
    api
      .post<{ agent_run_id: string; reference_id: string }>(
        `/content/references/${id}/extract-dna/`,
      )
      .then((r) => r.data),
}

export const styleRulesApi = {
  list: (params?: { status?: string; brand?: string }) =>
    api
      .get<Paginated<StyleRule>>('/content/style-rules/', { params })
      .then((r) => unwrapList(r.data)),
  approve: (id: string) =>
    api.post<StyleRule>(`/content/style-rules/${id}/approve/`).then((r) => r.data),
  reject: (id: string) =>
    api.post<StyleRule>(`/content/style-rules/${id}/reject/`).then((r) => r.data),
}

export const agentRunsApi = {
  get: (id: string) => api.get<AgentRun>(`/agent-runs/${id}/`).then((r) => r.data),
}
