"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import { makeEmptyFormData, type CampaignFormData, type Step } from "@/components/campaigns/create/types"
import Step1Basics from "@/components/campaigns/create/Step1Basics"
import Step2Upload, { type ParsedCsv } from "@/components/campaigns/create/Step2Upload"
import Step3Review from "@/components/campaigns/create/Step3Review"

function countWords(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) return 0
  return trimmed.split(/\s+/).length
}

function StepDot({ n, current }: { n: Step; current: Step }) {
  const active = n === current
  const done = n < current
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "h-7 w-7 rounded-full border text-xs font-semibold flex items-center justify-center",
          active ? "bg-slate-900 text-white border-slate-900" : done ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-white text-slate-600 border-slate-200",
        )}
      >
        {n}
      </div>
    </div>
  )
}

export default function CreateCampaignModal({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (campaignId: string) => void
}) {
  const [step, setStep] = React.useState<Step>(1)
  const [formData, setFormData] = React.useState<CampaignFormData>(() => makeEmptyFormData())
  const [csv, setCsv] = React.useState<ParsedCsv | null>(null)
  const [launchError, setLaunchError] = React.useState<string | null>(null)
  const [isLaunching, setIsLaunching] = React.useState(false)
  const launchRef = React.useRef<null | (() => void)>(null)

  const resetAll = React.useCallback(() => {
    setStep(1)
    setFormData(makeEmptyFormData())
    setCsv(null)
    setLaunchError(null)
    setIsLaunching(false)
    launchRef.current = null
  }, [])

  React.useEffect(() => {
    if (!open) resetAll()
  }, [open, resetAll])

  const valuePropWords = countWords(formData.valueProp)

  const canNext = React.useMemo(() => {
    if (step === 1) {
      return (
        formData.name.trim().length > 0 &&
        formData.product.trim().length > 0 &&
        formData.valueProp.trim().length > 0 &&
        formData.caseStudy.trim().length > 0 &&
        valuePropWords <= 100
      )
    }

    if (step === 2) {
      return (
        Boolean(formData.file) &&
        Boolean(formData.columnMapping.company_name) &&
        Boolean(formData.columnMapping.email) &&
        formData.validRows > 0
      )
    }

    return true
  }, [formData, step, valuePropWords])

  const title = step === 1 ? "Campaign basics" : step === 2 ? "Upload & map leads" : "Review & launch"
  const subtitle = step === 1
    ? "Set the essentials — you can refine copy later."
    : step === 2
      ? "Upload a CSV and confirm how columns map."
      : "Double-check before launching — this is a commitment."

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen)
      }}
    >
      <DialogContent className="overflow-hidden">
        <DialogHeader className="border-b pb-4">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription>{subtitle}</DialogDescription>
            </div>
            <div className="flex items-center gap-3">
              <StepDot n={1} current={step} />
              <div className="h-px w-6 bg-slate-200" />
              <StepDot n={2} current={step} />
              <div className="h-px w-6 bg-slate-200" />
              <StepDot n={3} current={step} />
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 py-5">
          {step === 1 ? (
            <Step1Basics formData={formData} setFormData={setFormData} />
          ) : step === 2 ? (
            <Step2Upload
              formData={formData}
              setFormData={setFormData}
              csv={csv}
              setCsv={setCsv}
            />
          ) : (
            <Step3Review
              formData={formData}
              launchError={launchError}
              setLaunchError={setLaunchError}
              setIsLaunching={setIsLaunching}
              setLaunchFn={(fn) => {
                launchRef.current = fn
              }}
              onDone={(id) => {
                onCreated?.(id)
                onOpenChange(false)
              }}
            />
          )}
        </div>

        <div className="flex items-center justify-between border-t px-6 py-4">
          <div className="text-xs text-slate-600">
            Step {step} of 3
          </div>
          <div className="flex items-center gap-2">
            {step > 1 && (
              <Button
                variant="outline"
                disabled={isLaunching}
                onClick={() => {
                  setLaunchError(null)
                  setStep((s) => (s === 1 ? 1 : ((s - 1) as Step)))
                }}
              >
                Back
              </Button>
            )}

            {step < 3 ? (
              <Button
                disabled={!canNext}
                onClick={() => {
                  setLaunchError(null)
                  setStep((s) => (s === 3 ? 3 : ((s + 1) as Step)))
                }}
              >
                Next
              </Button>
            ) : (
              <Button
                disabled={isLaunching}
                onClick={() => {
                  setLaunchError(null)
                  launchRef.current?.()
                }}
              >
                {isLaunching ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Launching...
                  </>
                ) : (
                  "Launch campaign"
                )}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
