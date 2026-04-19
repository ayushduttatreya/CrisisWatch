import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { EntitiesData } from "@/types"

interface EntityLeaderboardProps {
  entities: EntitiesData | null
}

export function EntityLeaderboard({ entities }: EntityLeaderboardProps) {
  if (!entities) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Entities (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  const { countries, organizations, people } = entities.top_entities

  const renderList = (items: { name: string; mentions: number }[], icon: string) => {
    if (items.length === 0) {
      return <div className="text-sm text-muted-foreground">No data yet</div>
    }

    return (
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.name}
            className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
          >
            <span className="text-sm">
              {icon} {item.name}
            </span>
            <Badge variant="secondary" className="text-xs">
              {item.mentions}
            </Badge>
          </div>
        ))}
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Entities (24h)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
            🌍 Countries
          </h4>
          {renderList(countries, "")}
        </div>
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
            🏢 Organizations
          </h4>
          {renderList(organizations, "")}
        </div>
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
            👤 People
          </h4>
          {renderList(people, "")}
        </div>
      </CardContent>
    </Card>
  )
}
