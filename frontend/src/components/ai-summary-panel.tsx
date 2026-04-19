import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { AISummary } from "@/types"

interface AISummaryPanelProps {
  summary: AISummary | null
}

export function AISummaryPanel({ summary }: AISummaryPanelProps) {
  if (!summary) return null

  return (
    <Card className="border-indigo-500/50 bg-indigo-950/30">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <CardTitle className="text-sm font-medium text-indigo-300">
            AI CRISIS ANALYSIS
          </CardTitle>
          {summary.cached && (
            <Badge variant="secondary" className="text-xs">Cached</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-indigo-100">
          {summary.summary}
        </p>
        <p className="mt-3 text-xs text-indigo-400">
          Based on {summary.headline_count} headlines
        </p>
      </CardContent>
    </Card>
  )
}
