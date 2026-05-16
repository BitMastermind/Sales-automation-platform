import CampaignDetailClient from "@/app/campaigns/[id]/CampaignDetailClient"

export default function Page({ params }: { params: { id: string } }) {
  const { id } = params
  return <CampaignDetailClient campaignId={id} />
}
