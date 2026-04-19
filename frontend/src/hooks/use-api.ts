import { useState, useEffect, useCallback } from 'react'
import type { Article, Stats, TrendData, EntitiesData, AISummary, NLQueryResponse } from '@/types'

const API_BASE = ''

export function useDashboardData() {
  const [articles, setArticles] = useState<Article[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [trend, setTrend] = useState<number[]>([])
  const [entities, setEntities] = useState<EntitiesData | null>(null)
  const [aiSummary, setAiSummary] = useState<AISummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [articlesRes, statsRes, trendRes, entitiesRes] = await Promise.all([
        fetch(`${API_BASE}/api/articles?limit=20&order=desc`),
        fetch(`${API_BASE}/api/stats`),
        fetch(`${API_BASE}/api/trend`),
        fetch(`${API_BASE}/api/entities?hours=24&top=5`)
      ])

      if (!articlesRes.ok || !statsRes.ok || !trendRes.ok) {
        throw new Error('API error')
      }

      const articlesData = await articlesRes.json()
      const statsData = await statsRes.json()
      const trendData = await trendRes.json()

      setArticles(articlesData.articles)
      setStats(statsData)
      setTrend(trendData.trend)

      if (entitiesRes.ok) {
        const entitiesData = await entitiesRes.json()
        setEntities(entitiesData)
      }

      // Fetch AI summary if spike is detected
      if (statsData.is_spike) {
        try {
          const summaryRes = await fetch(`${API_BASE}/api/ai/summary`)
          if (summaryRes.ok) {
            const summaryData = await summaryRes.json()
            if (summaryData.summary) {
              setAiSummary(summaryData)
            }
          }
        } catch (e) {
          console.log('AI summary not available')
        }
      } else {
        setAiSummary(null)
      }

      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData])

  return { articles, stats, trend, entities, aiSummary, loading, error, refetch: fetchData }
}

export async function queryNews(q: string): Promise<NLQueryResponse> {
  const res = await fetch(`/api/ai/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q, max_context: 20 })
  })

  if (!res.ok) {
    throw new Error('Failed to query')
  }

  return res.json()
}
