export type Step = 1 | 2 | 3

export type CampaignTone = "professional_friendly" | "direct" | "warm"

export type ColumnKey = "company_name" | "email" | "website" | "contact_name"

export type ColumnMapping = Record<ColumnKey, string | null>

export interface InvalidRow {
  rowIndex: number
  reason: string
}

export interface ParsedRow {
  company_name: string
  email: string
  website?: string
  contact_name?: string
  isValid: boolean
}

export interface CampaignFormData {
  name: string
  product: string
  valueProp: string
  caseStudy: string
  tone: CampaignTone
  file: File | null
  columnMapping: ColumnMapping
  parsedRows: ParsedRow[]
  validRows: number
  invalidRows: InvalidRow[]
}

export function makeEmptyFormData(): CampaignFormData {
  return {
    name: "",
    product: "",
    valueProp: "",
    caseStudy: "",
    tone: "professional_friendly",
    file: null,
    columnMapping: {
      company_name: null,
      email: null,
      website: null,
      contact_name: null,
    },
    parsedRows: [],
    validRows: 0,
    invalidRows: [],
  }
}

