export interface Article {
  id: number
  title: string
  source: string
  sentiment: number
  category: string
  url: string
  fetched_at: string
  entities?: {
    people: string[]
    countries: string[]
    organizations: string[]
  }
  bias?: string
  bias_confidence?: number
}

export interface Stats {
  total: number
  mood_avg: number
  is_spike: boolean
  alerts: Alert[]
}

export interface Alert {
  type: string
  msg: string
  time: string
}

export interface TrendData {
  trend: number[]
}

export interface EntityItem {
  name: string
  mentions: number
}

export interface EntitiesData {
  top_entities: {
    people: EntityItem[]
    countries: EntityItem[]
    organizations: EntityItem[]
  }
  time_window_hours: number
  articles_analyzed: number
}

export interface AISummary {
  summary: string
  generated_at: string
  headline_count: number
  cached?: boolean
}

export interface NLQueryResponse {
  answer: string
  sources_used: number
  generated_at: string
  success: boolean
}
