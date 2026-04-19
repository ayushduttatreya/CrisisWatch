"use client"

import { Area, AreaChart, CartesianGrid, XAxis, YAxis, ReferenceLine } from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface ChartAreaInteractiveProps {
  data: number[]
  isSpike?: boolean
}

export function ChartAreaInteractive({ data, isSpike }: ChartAreaInteractiveProps) {
  // Transform data for recharts
  const chartData = data.map((value, index) => ({
    index,
    sentiment: value,
  }))

  return (
    <Card>
      <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
        <div className="grid flex-1 gap-1 text-center sm:text-left">
          <CardTitle>Sentiment Trend</CardTitle>
          <CardDescription>
            Rolling average over last {data.length} data points
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        <div className="h-[250px] w-full">
          {data.length > 0 ? (
            <AreaChart
              width={600}
              height={250}
              data={chartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="index" 
                hide 
              />
              <YAxis 
                domain={[-1, 1]} 
                tickFormatter={(value) => value.toFixed(1)}
                stroke="#64748b"
                fontSize={12}
              />
              <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
              {isSpike && (
                <ReferenceLine 
                  y={-0.3} 
                  stroke="#ef4444" 
                  strokeDasharray="5 5"
                  label={{ value: "Crisis Threshold", fill: "#ef4444", fontSize: 12 }}
                />
              )}
              <Area
                type="monotone"
                dataKey="sentiment"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorSentiment)"
              />
            </AreaChart>
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Waiting for data...
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
