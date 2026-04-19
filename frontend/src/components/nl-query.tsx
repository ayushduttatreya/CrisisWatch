import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { queryNews } from "@/hooks/use-api"

export function NLQuery() {
  const [query, setQuery] = useState("")
  const [response, setResponse] = useState<string | null>(null)
  const [sourcesUsed, setSourcesUsed] = useState(0)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const result = await queryNews(query)
      setResponse(result.answer)
      setSourcesUsed(result.sources_used)
    } catch (e) {
      setResponse("Failed to get response. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask the News</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="What is happening in Ukraine?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Thinking..." : "Ask"}
          </Button>
        </div>
        {response && (
          <div className="rounded-md bg-muted p-4">
            <p className="text-sm leading-relaxed">{response}</p>
            {sourcesUsed > 0 && (
              <p className="mt-2 text-xs text-muted-foreground">
                Sources: {sourcesUsed} articles
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
