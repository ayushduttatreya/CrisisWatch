import { useState, useEffect, useCallback } from 'react'
import type { Article, Stats, EntitiesData, AISummary, NLQueryResponse } from '@/types'

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
      // Fetch all data in parallel, but handle each failure independently
      const [
        articlesRes,
        statsRes,
        trendRes,
        entitiesRes
      ] = await Promise.allSettled([
        fetch(`${API_BASE}/api/articles?limit=20&order=desc`),
        fetch(`${API_BASE}/api/stats`),
        fetch(`${API_BASE}/api/trend`),
        fetch(`${API_BASE}/api/entities?hours=24&top=5`)
      ])

      // Process articles
      if (articlesRes.status === 'fulfilled' && articlesRes.value.ok) {
        const data = await articlesRes.value.json()
        setArticles(data.articles || [])
      } else {
        console.error('Failed to fetch articles')
        setArticles([])
      }

      // Process stats
      let spikeDetected = false
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const data = await statsRes.value.json()
        setStats(data)
        spikeDetected = data.is_spike || false
      } else {
        console.error('Failed to fetch stats')
        setStats({ total: 0, mood_avg: 0, is_spike: false, alerts: [] })
      }

      // Process trend
      if (trendRes.status === 'fulfilled' && trendRes.value.ok) {
        const data = await trendRes.value.json()
        setTrend(data.trend || [])
      } else {
        console.error('Failed to fetch trend')
        setTrend([])
      }

      // Process entities (optional)
      if (entitiesRes.status === 'fulfilled' && entitiesRes.value.ok) {
        const data = await entitiesRes.value.json()
        setEntities(data)
      } else {
        setEntities(null)
      }

      // Fetch AI summary only if spike detected
      if (spikeDetected) {
        try {
          const summaryRes = await fetch(`${API_BASE}/api/ai/summary`)
          if (summaryRes.ok) {
            const summaryData = await summaryRes.json()
            if (summaryData.summary) {
              setAiSummary(summaryData)
            } else {
              setAiSummary(null)
            }
          }
        } catch (e) {
          console.log('AI summary not available')
          setAiSummary(null)
        }
      } else {
        setAiSummary(null)
      }

      setError(null)
    } catch (err) {
      console.error('Dashboard data fetch error:', err)
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
