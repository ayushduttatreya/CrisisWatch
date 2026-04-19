import { Newspaper, Activity, TrendingDown, Database } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/utils/cn"

interface SectionCardsProps {
  total: number
  moodAvg: number
  isSpike: boolean
  trendPoints: number
}

export function SectionCards({ total, moodAvg, isSpike, trendPoints }: SectionCardsProps) {
  const cards = [
    {
      title: "Total Articles",
      value: total.toLocaleString(),
      icon: Database,
      trend: null,
      trendUp: null,
    },
    {
      title: "Global Sentiment",
      value: moodAvg.toFixed(2),
      icon: Activity,
      trend: isSpike ? "Crisis" : "Normal",
      trendUp: !isSpike,
    },
    {
      title: "Trend Points",
      value: trendPoints.toString(),
      icon: TrendingDown,
      trend: "Rolling window",
      trendUp: null,
    },
    {
      title: "Articles/Hour",
      value: "~60",
      icon: Newspaper,
      trend: "Est. rate",
      trendUp: null,
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            <card.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            {card.trend && (
              <p
                className={cn(
                  "text-xs",
                  card.trendUp === null
                    ? "text-muted-foreground"
                    : card.trendUp
                    ? "text-green-500"
                    : "text-red-500"
                )}
              >
                {card.trend}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
