import { Globe, AlertTriangle, TrendingDown, Settings } from "lucide-react"
import { cn } from "@/utils/cn"

interface AppSidebarProps {
  className?: string
}

export function AppSidebar({ className }: AppSidebarProps) {
  return (
    <div className={cn("flex h-full flex-col border-r bg-card", className)}>
      <div className="flex h-14 items-center border-b px-4">
        <Globe className="mr-2 h-5 w-5 text-primary" />
        <span className="font-semibold">CrisisWatch</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        <a
          href="#"
          className="flex items-center gap-3 rounded-lg bg-primary/10 px-3 py-2 text-primary transition-all"
        >
          <TrendingDown className="h-4 w-4" />
          Dashboard
        </a>
        <a
          href="#alerts"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
        >
          <AlertTriangle className="h-4 w-4" />
          Alerts
        </a>
        <a
          href="#settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
        >
          <Settings className="h-4 w-4" />
          Settings
        </a>
      </nav>
    </div>
  )
}
