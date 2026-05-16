"use client"

import * as React from "react"

import type { CampaignFormData, CampaignTone } from "@/components/campaigns/create/types"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"

function countWords(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) return 0
  return trimmed.split(/\s+/).length
}

function ToneButton({
  label,
  value,
  selected,
  onSelect,
}: {
  label: string
  value: CampaignTone
  selected: boolean
  onSelect: (v: CampaignTone) => void
}) {
  return (
    <Button
      type="button"
      variant={selected ? "default" : "outline"}
      className={cn("h-8", selected ? "" : "bg-white")}
      onClick={() => onSelect(value)}
    >
      {label}
    </Button>
  )
}

export default function Step1Basics({
  formData,
  setFormData,
}: {
  formData: CampaignFormData
  setFormData: React.Dispatch<React.SetStateAction<CampaignFormData>>
}) {
  const words = countWords(formData.valueProp)
  const counterColor =
    words >= 100 ? "text-rose-700" : words >= 90 ? "text-amber-700" : "text-slate-600"

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="campaign-name">Campaign name</Label>
          <Input
            id="campaign-name"
            value={formData.name}
            maxLength={80}
            placeholder="Example: Logistics CTOs — Q2 outbound"
            onChange={(e) =>
              setFormData((p) => ({
                ...p,
                name: e.target.value,
              }))
            }
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="campaign-product">Product / service</Label>
          <Input
            id="campaign-product"
            value={formData.product}
            maxLength={80}
            placeholder="Example: AI SDR assistant"
            onChange={(e) =>
              setFormData((p) => ({
                ...p,
                product: e.target.value,
              }))
            }
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="campaign-valueprop">Value proposition</Label>
        <textarea
          id="campaign-valueprop"
          value={formData.valueProp}
          rows={4}
          placeholder="In one sentence, what makes this offer compelling?"
          className={cn(
            "w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
            words > 100 ? "border-rose-300 focus-visible:border-rose-500 focus-visible:ring-rose-500/20" : "",
          )}
          onChange={(e) =>
            setFormData((p) => ({
              ...p,
              valueProp: e.target.value,
            }))
          }
        />
        <div className={cn("text-xs", counterColor)}>
          {words} / 100 words
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="campaign-casestudy">Case study</Label>
        <textarea
          id="campaign-casestudy"
          value={formData.caseStudy}
          rows={4}
          placeholder="Example: We helped LogiCorp reduce manual outreach by 40% in 3 months"
          className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          onChange={(e) =>
            setFormData((p) => ({
              ...p,
              caseStudy: e.target.value,
            }))
          }
        />
      </div>

      <div className="space-y-2">
        <Label>Tone</Label>
        <div className="inline-flex items-center gap-2 rounded-lg border bg-slate-50 p-1">
          <ToneButton
            label="Professional & Friendly"
            value="professional_friendly"
            selected={formData.tone === "professional_friendly"}
            onSelect={(tone) => setFormData((p) => ({ ...p, tone }))}
          />
          <ToneButton
            label="Direct"
            value="direct"
            selected={formData.tone === "direct"}
            onSelect={(tone) => setFormData((p) => ({ ...p, tone }))}
          />
          <ToneButton
            label="Warm"
            value="warm"
            selected={formData.tone === "warm"}
            onSelect={(tone) => setFormData((p) => ({ ...p, tone }))}
          />
        </div>
      </div>
    </div>
  )
}

