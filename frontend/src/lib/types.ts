export interface ApiErrorShape {
  code: string
  message: string
}

export interface ApiEnvelope<T> {
  data: T
  error: ApiErrorShape | null
  meta: Record<string, unknown>
}

export interface Meta {
  page: number
  size: number
  total: number
}

export type CampaignStatus = "draft" | "active" | "paused" | "completed"

export interface CampaignStats {
  leads_count: number
  emails_sent: number
  open_rate: number
  reply_rate: number
  meetings_booked: number
}

export interface Campaign {
  id: string
  name: string
  status: CampaignStatus | string
  settings?: Record<string, unknown> | null
  created_at: string
  updated_at?: string | null
  stats?: CampaignStats
}

export type CampaignDetail = Campaign & {
  stats: CampaignStats
}

export type LeadStatus =
  | "new"
  | "researched"
  | "email_sent"
  | "replied"
  | "meeting_booked"
  | "unsubscribed"

export interface Lead {
  id: string
  campaign_id: string
  company_name: string
  email: string
  website?: string | null
  contact_name?: string | null
  status: LeadStatus | string
  research_data?: Record<string, unknown> | null
  created_at: string
}

export type EmailType = "outreach" | "followup"

export interface Reply {
  id: string
  email_id: string
  content: string
  classified_as: string
  received_at: string
}

export interface Email {
  id: string
  lead_id: string
  subject?: string | null
  body?: string | null
  type: EmailType | string
  sent_at?: string | null
  opened_at?: string | null
  replied_at?: string | null
  gmail_message_id?: string | null
  replies?: Reply[]
}

export type LeadDetail = Lead & {
  emails: Email[]
}

export interface UploadErrorRow {
  row: number
  reason: string
}

export interface UploadResult {
  inserted: number
  skipped: number
  errors: UploadErrorRow[]
}

export type TemplateType = "intro" | "followup" | "re_engagement"

export interface Template {
  id: string
  name: string
  type: TemplateType
  subject: string
  body: string
  tags: string[]
  used_count: number
  created_at: string
}

export type IntegrationStatus = "connected" | "disconnected" | "coming_soon"

export interface Integration {
  id: string
  name: string
  description: string
  category: "email" | "crm" | "enrichment" | "automation"
  status: IntegrationStatus
  connected_email?: string | null
  connected_at?: string | null
}

