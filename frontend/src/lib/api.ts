import type {
  ApiEnvelope,
  Campaign,
  CampaignDetail,
  Integration,
  Lead,
  LeadDetail,
  Meta,
  Template,
  UploadResult,
} from "@/lib/types"
import {
  MOCK_CAMPAIGNS,
  MOCK_CAMPAIGN_DETAIL,
  MOCK_INTEGRATIONS,
  MOCK_LEADS,
  MOCK_LEAD_DETAIL,
  MOCK_TEMPLATES,
  mockMeta,
} from "@/lib/mock-data"

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true"

export class ApiError extends Error {
  public readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = "ApiError"
    this.code = code
  }
}

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE
  if (!base) {
    throw new Error("Missing env var: NEXT_PUBLIC_API_BASE")
  }
  return base.replace(/\/+$/, "")
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiEnvelope<T>> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  })

  const json = (await res.json().catch(() => null)) as ApiEnvelope<T> | null

  if (!res.ok) {
    throw new ApiError(
      "HTTP_ERROR",
      `API error ${res.status}`,
    )
  }

  const envelope = json as ApiEnvelope<T> | null

  if (!envelope) {
    throw new ApiError(
      "BAD_RESPONSE",
      `Unexpected response from API (${res.status})`,
    )
  }

  if (envelope.error) {
    throw new ApiError(envelope.error.code, envelope.error.message)
  }

  return envelope
}

export async function fetchCampaigns(
  page: number,
  size: number,
): Promise<{ data: Campaign[]; meta: Meta }> {
  if (USE_MOCK) {
    const start = (page - 1) * size
    const slice = MOCK_CAMPAIGNS.slice(start, start + size)
    return { data: slice, meta: mockMeta(MOCK_CAMPAIGNS.length, page, size) }
  }
  const env = await request<Campaign[]>(`/api/campaigns?page=${page}&size=${size}`)
  const meta = env.meta as unknown as Meta
  return { data: env.data, meta }
}

export async function fetchCampaign(
  id: string,
): Promise<{ data: CampaignDetail }> {
  if (USE_MOCK) {
    const detail = MOCK_CAMPAIGN_DETAIL[id] ?? MOCK_CAMPAIGN_DETAIL["camp-001"]
    return { data: detail }
  }
  const env = await request<CampaignDetail>(`/api/campaigns/${id}`)
  return { data: env.data }
}

export async function patchCampaignStatus(
  id: string,
  status: string,
): Promise<void> {
  if (USE_MOCK) return
  await request(`/api/campaigns/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  })
}

export async function createCampaign(input: {
  name: string
  settings?: Record<string, unknown> | null
}): Promise<Campaign> {
  if (USE_MOCK) {
    return {
      id: `camp-mock-${Date.now()}`,
      name: input.name,
      status: "draft",
      created_at: new Date().toISOString(),
      stats: { leads_count: 0, emails_sent: 0, open_rate: 0, reply_rate: 0, meetings_booked: 0 },
    }
  }
  const env = await request<Campaign>(`/api/campaigns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      settings: input.settings ?? null,
    }),
  })
  return env.data
}

export async function uploadLeads(
  campaignId: string,
  file: File,
): Promise<UploadResult> {
  if (USE_MOCK) return { inserted: 42, skipped: 0, errors: [] }
  const form = new FormData()
  form.append("file", file)
  form.append("campaign_id", campaignId)
  const env = await request<UploadResult>(`/api/leads/upload`, {
    method: "POST",
    body: form,
  })
  return env.data
}

export async function fetchLeads(
  campaignId: string,
  page: number,
): Promise<{ data: Lead[]; meta: Meta }> {
  if (USE_MOCK) {
    const all = MOCK_LEADS[campaignId] ?? MOCK_LEADS["camp-001"]
    const size = 20
    const start = (page - 1) * size
    return { data: all.slice(start, start + size), meta: mockMeta(all.length, page, size) }
  }
  const env = await request<Lead[]>(
    `/api/leads?campaign_id=${campaignId}&page=${page}&size=20`,
  )
  const meta = env.meta as unknown as Meta
  return { data: env.data, meta }
}

export async function fetchLead(id: string): Promise<{ data: LeadDetail }> {
  if (USE_MOCK) {
    const detail = MOCK_LEAD_DETAIL[id] ?? MOCK_LEAD_DETAIL["lead-001"]
    return { data: detail }
  }
  const env = await request<LeadDetail>(`/api/leads/${id}`)
  return { data: env.data }
}

export async function fetchAllLeads(
  page: number,
  campaignId?: string,
  status?: string,
): Promise<{ data: Lead[]; meta: Meta }> {
  if (USE_MOCK) {
    const allLeads = Object.values(MOCK_LEADS).flat()
    const filtered = allLeads
      .filter((l) => !campaignId || l.campaign_id === campaignId)
      .filter((l) => !status || l.status === status)
    const size = 20
    const start = (page - 1) * size
    return { data: filtered.slice(start, start + size), meta: mockMeta(filtered.length, page, size) }
  }
  const params = new URLSearchParams({ page: String(page), size: "20" })
  if (campaignId) params.set("campaign_id", campaignId)
  if (status) params.set("status", status)
  const env = await request<Lead[]>(`/api/leads?${params}`)
  return { data: env.data, meta: env.meta as unknown as Meta }
}

export async function fetchTemplates(): Promise<Template[]> {
  if (USE_MOCK) return MOCK_TEMPLATES
  const env = await request<Template[]>("/api/templates")
  return env.data
}

export async function fetchIntegrations(): Promise<Integration[]> {
  if (USE_MOCK) return MOCK_INTEGRATIONS
  const env = await request<Integration[]>("/api/integrations")
  return env.data
}
