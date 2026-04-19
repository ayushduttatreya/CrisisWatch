import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { SectionCards } from "@/components/section-cards"
import { SiteHeader } from "@/components/site-header"
import { AISummaryPanel } from "@/components/ai-summary-panel"
import { EntityLeaderboard } from "@/components/entity-leaderboard"
import { NLQuery } from "@/components/nl-query"
import { useDashboardData } from "@/hooks/use-api"
import { Skeleton } from "@/components/ui/skeleton"

function App() {
  const { articles, stats, trend, entities, aiSummary, loading } = useDashboardData()

  if (loading) {
    return (
      <div className="flex h-screen bg-background">
        <div className="w-64 border-r bg-card" />
        <div className="flex-1 p-6">
          <Skeleton className="h-8 w-48 mb-6" />
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-[300px] mb-6" />
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      <AppSidebar className="w-64 shrink-0" />
      <div className="flex-1 flex flex-col overflow-hidden">
        <SiteHeader />
        <main className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-7xl space-y-6">
            <SectionCards
              total={stats?.total || 0}
              moodAvg={stats?.mood_avg || 0}
              isSpike={stats?.is_spike || false}
              trendPoints={trend?.length || 0}
            />
            
            {aiSummary && <AISummaryPanel summary={aiSummary} />}
            
            <ChartAreaInteractive data={trend || []} isSpike={stats?.is_spike} />
            
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <DataTable data={articles} />
              </div>
              <div className="space-y-6">
                <NLQuery />
                <EntityLeaderboard entities={entities} />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
