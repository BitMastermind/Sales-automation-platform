import { Badge } from "@/components/ui/badge"

type Tone =
  | "gray"
  | "green"
  | "amber"
  | "blue"
  | "purple"
  | "slate"
  | "rose"

function toneForCampaign(status: string): Tone {
  switch (status) {
    case "draft":
      return "gray"
    case "active":
      return "green"
    case "paused":
      return "amber"
    case "completed":
      return "blue"
    default:
      return "slate"
  }
}

function toneForLead(status: string): Tone {
  switch (status) {
    case "new":
      return "gray"
    case "researched":
      return "blue"
    case "email_sent":
      return "purple"
    case "replied":
      return "amber"
    case "meeting_booked":
      return "green"
    case "unsubscribed":
      return "slate"
    default:
      return "slate"
  }
}

function classForTone(tone: Tone): string {
  switch (tone) {
    case "gray":
      return "bg-slate-100 text-slate-800 border-slate-200"
    case "green":
      return "bg-emerald-50 text-emerald-800 border-emerald-200"
    case "amber":
      return "bg-amber-50 text-amber-800 border-amber-200"
    case "blue":
      return "bg-sky-50 text-sky-800 border-sky-200"
    case "purple":
      return "bg-violet-50 text-violet-800 border-violet-200"
    case "rose":
      return "bg-rose-50 text-rose-800 border-rose-200"
    case "slate":
    default:
      return "bg-slate-50 text-slate-800 border-slate-200"
  }
}

export default function StatusBadge({
  value,
  kind,
}: {
  value: string
  kind: "campaign" | "lead" | "generic"
}) {
  const tone =
    kind === "campaign"
      ? toneForCampaign(value)
      : kind === "lead"
        ? toneForLead(value)
        : "slate"
  return (
    <Badge
      variant="outline"
      className={[
        "rounded-full px-2.5 py-0.5 text-xs font-medium capitalize border",
        classForTone(tone),
      ].join(" ")}
    >
      {value.replaceAll("_", " ")}
    </Badge>
  )
}

