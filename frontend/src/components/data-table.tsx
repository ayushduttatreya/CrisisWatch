import { useState } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Article } from "@/types"

interface DataTableProps {
  data: Article[]
}

export function DataTable({ data }: DataTableProps) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  const getSentimentBadge = (sentiment: number) => {
    if (sentiment > 0.05) return <Badge className="bg-green-500/20 text-green-500 hover:bg-green-500/30">Positive</Badge>
    if (sentiment < -0.05) return <Badge className="bg-red-500/20 text-red-500 hover:bg-red-500/30">Negative</Badge>
    return <Badge className="bg-gray-500/20 text-gray-400 hover:bg-gray-500/30">Neutral</Badge>
  }

  const getBiasBadge = (bias?: string, confidence?: number) => {
    if (!bias) return null
    
    const colors: Record<string, string> = {
      left: "bg-blue-500/20 text-blue-400",
      right: "bg-red-500/20 text-red-400",
      neutral: "bg-green-500/20 text-green-400",
      unknown: "bg-gray-500/20 text-gray-400",
    }
    
    const icons: Record<string, string> = {
      left: "←",
      right: "→",
      neutral: "◆",
      unknown: "?",
    }
    
    const confText = confidence ? ` ${(confidence * 100).toFixed(0)}%` : ""
    
    return (
      <Badge className={`${colors[bias] || colors.unknown} hover:opacity-80`}>
        {icons[bias] || "?"}{confText}
      </Badge>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest Headlines</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Headline</TableHead>
                <TableHead className="w-[100px]">Source</TableHead>
                <TableHead className="w-[100px]">Sentiment</TableHead>
                <TableHead className="w-[100px]">Bias</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    No articles yet
                  </TableCell>
                </TableRow>
              ) : (
                data.map((article) => (
                  <TableRow 
                    key={article.id}
                    className="cursor-pointer"
                    onClick={() => setExpandedRow(expandedRow === article.id ? null : article.id)}
                  >
                    <TableCell>
                      <a 
                        href={article.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="font-medium hover:text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {article.title}
                      </a>
                      {expandedRow === article.id && article.entities && (
                        <div className="mt-2 text-sm text-muted-foreground">
                          {article.entities.countries.length > 0 && (
                            <div>Countries: {article.entities.countries.join(", ")}</div>
                          )}
                          {article.entities.people.length > 0 && (
                            <div>People: {article.entities.people.join(", ")}</div>
                          )}
                          {article.entities.organizations.length > 0 && (
                            <div>Orgs: {article.entities.organizations.join(", ")}</div>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{article.source}</TableCell>
                    <TableCell>{getSentimentBadge(article.sentiment)}</TableCell>
                    <TableCell>{getBiasBadge(article.bias, article.bias_confidence)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
