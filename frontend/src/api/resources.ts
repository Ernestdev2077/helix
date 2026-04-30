import { api } from './client'

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

export interface PostVariant {
  id: string
  post: string
  platform: Platform
  label: string
  content: string
  media: unknown[]
  status: string
  is_starred: boolean
  critic_notes: { severity: string; message: string; fix_suggestion?: string }[]
  allocation_weight: number
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

export interface Reference {
  id: string
  brand: string
  platform: Platform
  source: string
  source_url: string
  raw_text: string
  tags: string[]
  source_metrics: Record<string, unknown>
  extracted_features: Record<string, unknown>
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

export const workspacesApi = {
  list: () => api.get<Workspace[]>('/workspaces/').then((r) => r.data),
  create: (data: { name: string }) =>
    api.post<Workspace>('/workspaces/', data).then((r) => r.data),
}

export const brandsApi = {
  list: () => api.get<Brand[]>('/brands/').then((r) => r.data),
  create: (data: Partial<Brand>) => api.post<Brand>('/brands/', data).then((r) => r.data),
  update: (id: string, data: Partial<Brand>) =>
    api.patch<Brand>(`/brands/${id}/`, data).then((r) => r.data),
}

export const postsApi = {
  list: () => api.get<Post[]>('/content/posts/').then((r) => r.data),
  create: (data: Partial<Post>) =>
    api.post<Post>('/content/posts/', data).then((r) => r.data),
  get: (id: string) => api.get<Post>(`/content/posts/${id}/`).then((r) => r.data),
  generate: (id: string) =>
    api.post<{ agent_run_id: string; post_id: string }>(`/content/posts/${id}/generate/`).then(
      (r) => r.data,
    ),
}

export const referencesApi = {
  list: (params?: { platform?: Platform; brand?: string }) =>
    api.get<Reference[]>('/content/references/', { params }).then((r) => r.data),
  create: (data: Partial<Reference>) =>
    api.post<Reference>('/content/references/', data).then((r) => r.data),
  remove: (id: string) => api.delete(`/content/references/${id}/`),
}

export const styleRulesApi = {
  list: (params?: { status?: string; brand?: string }) =>
    api.get<StyleRule[]>('/content/style-rules/', { params }).then((r) => r.data),
  approve: (id: string) =>
    api.post<StyleRule>(`/content/style-rules/${id}/approve/`).then((r) => r.data),
  reject: (id: string) =>
    api.post<StyleRule>(`/content/style-rules/${id}/reject/`).then((r) => r.data),
}

export const agentRunsApi = {
  get: (id: string) => api.get<AgentRun>(`/agent-runs/${id}/`).then((r) => r.data),
}
