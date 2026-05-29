import { use } from "react"
import CampaignDetailClient from "@/app/campaigns/[id]/CampaignDetailClient"

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <CampaignDetailClient campaignId={id} />
}
