import SettingsClient from "@/app/settings/SettingsClient"
import { Suspense } from "react"

export default function Page() {
  const envOk = {
    NEXT_PUBLIC_API_BASE: Boolean(process.env.NEXT_PUBLIC_API_BASE),
  }

  return (
    <Suspense fallback={null}>
      <SettingsClient envOk={envOk} />
    </Suspense>
  )
}
