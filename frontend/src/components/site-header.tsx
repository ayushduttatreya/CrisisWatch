import { Activity } from "lucide-react"

export function SiteHeader() {
  return (
    <header className="flex h-14 items-center gap-4 border-b bg-card px-6">
      <div className="flex flex-1 items-center gap-2">
        <Activity className="h-5 w-5 text-green-500" />
        <span className="text-sm text-muted-foreground">System Operational</span>
      </div>
      <div className="text-sm text-muted-foreground">
        Live News Intelligence
      </div>
    </header>
  )
}
