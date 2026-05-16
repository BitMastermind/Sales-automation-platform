"use client"

import * as React from "react"
import { useDropzone } from "react-dropzone"
import { CloudUpload, Trash2, TriangleAlert } from "lucide-react"

import type { CampaignFormData, ColumnKey, ColumnMapping, InvalidRow, ParsedRow } from "@/components/campaigns/create/types"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export type ParsedCsv = { headers: string[]; rows: string[][] }

function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—"
  const kb = n / 1024
  if (kb < 1024) return `${kb.toFixed(0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

function normalizeHeader(h: string): string {
  return h.trim().replace(/^"(.*)"$/, "$1").trim()
}

function headerKey(h: string): string {
  return normalizeHeader(h)
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "")
}

function autoDetect(headers: string[], key: ColumnKey): string | null {
  const candidates: Record<ColumnKey, string[]> = {
    company_name: ["company", "company_name", "companyname", "account", "organization", "org", "business", "name", "companyname"],
    email: ["email", "email_address", "emailaddress", "work_email", "workemail", "e_mail"],
    website: ["website", "web", "url", "site", "domain", "homepage"],
    contact_name: ["contact", "contact_name", "contactname", "name", "full_name", "fullname", "person", "first_name", "firstname"],
  }

  const wants = new Set(candidates[key])
  for (const h of headers) {
    const hk = headerKey(h)
    if (wants.has(hk)) return h
  }
  return null
}

function parseCsv(text: string): ParsedCsv {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n")
  const lines = normalized
    .split("\n")
    .map((l) => l.trimEnd())
    .filter((l) => l.trim().length > 0)

  if (lines.length === 0) return { headers: [], rows: [] }
  const headers = lines[0].split(",").map(normalizeHeader).filter((h) => h.length > 0)
  const rows = lines.slice(1).map((l) => l.split(",").map((c) => c.trim()))
  return { headers, rows }
}

function buildRowObject(
  headers: string[],
  row: string[],
  mapping: ColumnMapping,
): { obj: Omit<ParsedRow, "isValid">; rawEmail: string | null } {
  const indexOf = (header: string | null): number => {
    if (!header) return -1
    return headers.findIndex((h) => headerKey(h) === headerKey(header))
  }

  const get = (key: ColumnKey): string | undefined => {
    const header = mapping[key]
    if (!header) return undefined
    const idx = indexOf(header)
    if (idx < 0) return undefined
    return row[idx]?.trim()
  }

  const company_name = get("company_name") ?? ""
  const email = get("email") ?? ""
  const website = get("website")
  const contact_name = get("contact_name")
  return {
    obj: {
      company_name,
      email,
      ...(website ? { website } : {}),
      ...(contact_name ? { contact_name } : {}),
    },
    rawEmail: email,
  }
}

function isLikelyEmail(v: string): boolean {
  const value = v.trim()
  if (!value) return false
  if (value.includes(" ")) return false
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

function computeValidation(csv: ParsedCsv, mapping: ColumnMapping): {
  parsedRows: ParsedRow[]
  validRows: number
  invalidRows: InvalidRow[]
} {
  const invalid: InvalidRow[] = []
  let valid = 0

  const parsed: ParsedRow[] = []
  csv.rows.forEach((row, i) => {
    const { obj, rawEmail } = buildRowObject(csv.headers, row, mapping)
    const ok =
      obj.company_name.trim().length > 0 &&
      Boolean(rawEmail) &&
      isLikelyEmail(rawEmail ?? "")

    if (ok) valid += 1
    else {
      const reason = !obj.company_name.trim()
        ? "Missing company name"
        : !rawEmail?.trim()
          ? "Missing email"
          : "Invalid email"
      invalid.push({ rowIndex: i + 2, reason })
    }

    if (parsed.length < 20) parsed.push({ ...obj, isValid: ok })
  })

  return { parsedRows: parsed, validRows: valid, invalidRows: invalid }
}

function SelectField({
  label,
  value,
  options,
  placeholder,
  onChange,
  required,
  allowNone,
}: {
  label: string
  value: string | null
  options: string[]
  placeholder: string
  onChange: (value: string | null) => void
  required?: boolean
  allowNone?: boolean
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <select
        className={cn(
          "h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
          required && !value ? "border-rose-300 focus-visible:border-rose-500 focus-visible:ring-rose-500/20" : "",
        )}
        value={value ?? (allowNone ? "__none__" : "")}
        onChange={(e) => {
          const v = e.target.value
          if (!v) onChange(null)
          else if (allowNone && v === "__none__") onChange(null)
          else onChange(v)
        }}
      >
        <option value="">{placeholder}</option>
        {allowNone ? <option value="__none__">Not in CSV</option> : null}
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function Step2Upload({
  formData,
  setFormData,
  csv,
  setCsv,
}: {
  formData: CampaignFormData
  setFormData: React.Dispatch<React.SetStateAction<CampaignFormData>>
  csv: ParsedCsv | null
  setCsv: React.Dispatch<React.SetStateAction<ParsedCsv | null>>
}) {
  const [parseError, setParseError] = React.useState<string | null>(null)

  const onDrop = React.useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0] ?? null
      setParseError(null)
      setCsv(null)
      setFormData((p) => ({
        ...p,
        file,
        columnMapping: {
          company_name: null,
          email: null,
          website: null,
          contact_name: null,
        },
        parsedRows: [],
        validRows: 0,
        invalidRows: [],
      }))
    },
    [setCsv, setFormData],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: { "text/csv": [".csv"] },
    multiple: false,
    noClick: true,
    onDrop,
  })

  React.useEffect(() => {
    if (!formData.file) return

    let cancelled = false
    const reader = new FileReader()
    reader.onload = () => {
      if (cancelled) return
      const text = typeof reader.result === "string" ? reader.result : ""
      try {
        const parsed = parseCsv(text)
        setParseError(null)
        setCsv(parsed)

        setFormData((p) => {
          const detected: ColumnMapping = {
            company_name: autoDetect(parsed.headers, "company_name"),
            email: autoDetect(parsed.headers, "email"),
            website: autoDetect(parsed.headers, "website"),
            contact_name: autoDetect(parsed.headers, "contact_name"),
          }

          const withNone = (v: string | null) => v
          const nextMapping: ColumnMapping = {
            company_name: withNone(detected.company_name),
            email: withNone(detected.email),
            website: withNone(detected.website),
            contact_name: withNone(detected.contact_name),
          }

          return {
            ...p,
            columnMapping: nextMapping,
            parsedRows: [],
            validRows: 0,
            invalidRows: [],
          }
        })
      } catch {
        setParseError("Could not parse this file. Please upload a valid CSV.")
        setCsv(null)
      }
    }
    reader.onerror = () => {
      if (cancelled) return
      setParseError("Could not read this file. Please try again.")
      setCsv(null)
    }

    reader.readAsText(formData.file)
    return () => {
      cancelled = true
      reader.abort()
    }
  }, [formData.file, setCsv, setFormData])

  const effectiveHeaders = csv?.headers ?? []

  const applyMapping = React.useCallback(
    (nextMapping: ColumnMapping) => {
      setFormData((p) => {
        if (!csv) {
          return { ...p, columnMapping: nextMapping }
        }

        const cleaned: ColumnMapping = nextMapping

        const canValidate = Boolean(cleaned.company_name) && Boolean(cleaned.email)
        const next = {
          ...p,
          columnMapping: cleaned,
        }

        if (!canValidate) {
          return { ...next, parsedRows: [], validRows: 0, invalidRows: [] }
        }

        const v = computeValidation(csv, cleaned)
        return { ...next, ...v }
      })
    },
    [csv, setFormData],
  )

  const file = formData.file

  const previewRows = formData.parsedRows.slice(0, 5)
  const invalidCount = formData.invalidRows.length

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>Upload CSV</Label>
        <div
          {...getRootProps()}
          className={cn(
            "rounded-xl border border-dashed p-5 transition-colors",
            isDragActive ? "border-slate-400 bg-slate-50" : "border-slate-200 bg-white",
          )}
        >
          <input {...getInputProps()} />
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-lg bg-slate-50 flex items-center justify-center border">
              <CloudUpload className="h-5 w-5 text-slate-700" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-900">
                Drop your CSV here or click to browse
              </div>
              <div className="text-xs text-slate-600">
                CSV only. We parse it locally in your browser.
              </div>
            </div>
            <Button type="button" variant="outline" onClick={open}>
              Browse
            </Button>
          </div>
        </div>

        {file ? (
          <div className="flex items-center justify-between rounded-lg border bg-slate-50 px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-slate-900">
                {file.name}
              </div>
              <div className="text-xs text-slate-600">
                {fmtBytes(file.size)}
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              className="text-slate-700"
              onClick={() => {
                setParseError(null)
                setCsv(null)
                setFormData((p) => ({
                  ...p,
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
                }))
              }}
            >
              <Trash2 className="h-4 w-4" />
              Remove
            </Button>
          </div>
        ) : null}

        {parseError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {parseError}
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-slate-900">Column mapping</div>
            <div className="text-xs text-slate-600">
              Required: company name + email. Optional fields can be left out.
            </div>
          </div>
        </div>

        <div className={cn("grid grid-cols-2 gap-4", !csv ? "opacity-60 pointer-events-none" : "")}>
          <SelectField
            label="Company name"
            required
            value={formData.columnMapping.company_name}
            placeholder={csv ? "Select a column" : "Upload a CSV first"}
            options={effectiveHeaders}
            onChange={(v) => applyMapping({ ...formData.columnMapping, company_name: v })}
          />
          <SelectField
            label="Email"
            required
            value={formData.columnMapping.email}
            placeholder={csv ? "Select a column" : "Upload a CSV first"}
            options={effectiveHeaders}
            onChange={(v) => applyMapping({ ...formData.columnMapping, email: v })}
          />
          <SelectField
            label="Website"
            allowNone
            value={formData.columnMapping.website}
            placeholder={csv ? "Optional" : "Upload a CSV first"}
            options={effectiveHeaders}
            onChange={(v) => applyMapping({ ...formData.columnMapping, website: v })}
          />
          <SelectField
            label="Contact name"
            allowNone
            value={formData.columnMapping.contact_name}
            placeholder={csv ? "Optional" : "Upload a CSV first"}
            options={effectiveHeaders}
            onChange={(v) => applyMapping({ ...formData.columnMapping, contact_name: v })}
          />
        </div>
      </div>

      <div className={cn("space-y-3", !csv ? "opacity-60 pointer-events-none" : "")}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-slate-900">Validation preview</div>
            <div className="text-xs text-slate-600">
              We’ll skip rows that are missing required fields or have invalid emails.
            </div>
          </div>
          <div className="text-xs text-slate-600 tabular-nums">
            {formData.validRows} valid rows, {invalidCount} will be skipped
          </div>
        </div>

        <div className="rounded-xl border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[40%]">Company</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-[24%]">Website</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {previewRows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} className="py-6 text-center text-sm text-slate-600">
                    Select company + email columns to preview validation.
                  </TableCell>
                </TableRow>
              ) : (
                previewRows.map((r, idx) => (
                  <TableRow
                    key={idx}
                    className={cn(r.isValid ? "" : "bg-rose-50")}
                  >
                    <TableCell className="font-medium">
                      {r.company_name || "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {!r.isValid ? (
                          <TriangleAlert className="h-4 w-4 text-rose-700" />
                        ) : null}
                        <span className={cn(!r.isValid ? "text-rose-800" : "")}>
                          {r.email || "—"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-700">
                      {r.website ?? "—"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
