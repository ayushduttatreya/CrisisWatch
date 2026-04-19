import { AlertTriangle, Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Alert } from "@/types"

interface AlertsPanelProps {
  alerts: Alert[]
  isSpike: boolean
}

export function AlertsPanel({ alerts, isSpike }: AlertsPanelProps) {
  if (!alerts || alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-green-500">
            <Info className="h-4 w-4" />
            <span className="text-sm">No active alerts</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={isSpike ? "border-red-500/50 bg-red-950/30" : ""}>
      <CardHeader>
        <div className="flex items-center gap-2">
          {isSpike && <AlertTriangle className="h-5 w-5 text-red-500" />}
          <CardTitle className="text-sm font-medium">
            {isSpike ? "CRISIS ALERT" : "System Alerts"}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 rounded-md px-3 py-2 text-sm ${
                alert.type === "crisis"
                  ? "bg-red-500/20 text-red-200"
                  : alert.type === "info"
                  ? "bg-blue-500/20 text-blue-200"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {alert.type === "crisis" && <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />}
              <div>
                <p>{alert.msg}</p>
                <p className="text-xs opacity-70 mt-1">
                  {new Date(alert.time).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
