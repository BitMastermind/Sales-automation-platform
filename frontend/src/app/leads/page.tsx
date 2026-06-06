import { Suspense } from "react"
import LeadsClient from "./LeadsClient"

export const metadata = { title: "Leads — SalesHQ" }

export default function LeadsPage() {
  return (
    <Suspense>
      <LeadsClient />
    </Suspense>
  )
}
