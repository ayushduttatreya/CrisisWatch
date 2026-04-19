# CrisisWatch Frontend

Modern React dashboard built with shadcn/ui, Vite, and Recharts.

## Development

```bash
# Install dependencies
npm install

# Start dev server (proxies API to localhost:5000)
npm run dev

# Build for production (outputs to ../static)
npm run build
```

## Features

- **shadcn/ui Components**: Modern, accessible UI components
- **Interactive Charts**: Recharts for sentiment trend visualization
- **Responsive Layout**: Sidebar + main content layout
- **Real-time Data**: Auto-refreshes every 30 seconds
- **AI Features**: Crisis summary, entity leaderboard, NL query

## Architecture

```
src/
├── components/
│   ├── ui/          # shadcn/ui components
│   ├── app-sidebar.tsx
│   ├── site-header.tsx
│   ├── section-cards.tsx
│   ├── chart-area-interactive.tsx
│   ├── data-table.tsx
│   ├── ai-summary-panel.tsx
│   ├── entity-leaderboard.tsx
│   └── nl-query.tsx
├── hooks/
│   └── use-api.ts   # API integration
├── types/
│   └── index.ts     # TypeScript types
├── utils/
│   └── cn.ts        # Utility functions
├── App.tsx
└── main.tsx
```
