import type {
  ApiEnvelope,
  Campaign,
  CampaignDetail,
  Lead,
  LeadDetail,
  Meta,
  UploadResult,
} from "@/lib/types"

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

  const json = (await res.json().catch(() => null)) as
    | ApiEnvelope<T>
    | { detail?: ApiEnvelope<T> }
    | null

  const envelope = (json && "detail" in json ? json.detail : json) as
    | ApiEnvelope<T>
    | null

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
  const env = await request<Campaign[]>(`/api/campaigns?page=${page}&size=${size}`)
  const meta = env.meta as unknown as Meta
  return { data: env.data, meta }
}

export async function fetchCampaign(
  id: string,
): Promise<{ data: CampaignDetail }> {
  const env = await request<CampaignDetail>(`/api/campaigns/${id}`)
  return { data: env.data }
}

export async function patchCampaignStatus(
  id: string,
  status: string,
): Promise<void> {
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
  const env = await request<Lead[]>(
    `/api/leads?campaign_id=${campaignId}&page=${page}&size=20`,
  )
  const meta = env.meta as unknown as Meta
  return { data: env.data, meta }
}

export async function fetchLead(id: string): Promise<{ data: LeadDetail }> {
  const env = await request<LeadDetail>(`/api/leads/${id}`)
  return { data: env.data }
}
