# Chronos Dashboard

Next.js dashboard for Project Chronos digital twin crisis system.

## Features

- **Live Event Feed** (`/`): Real-time display of last 50 events
- **Sector Map** (`/map`): Grid view of 3 sectors with color-coded status
- **Audit Decisions** (`/audit`): List of audit decisions with Solana hash

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env.local
# Edit .env.local with your MongoDB connection details
```

3. Run development server:
```bash
npm run dev
```

The dashboard will be available at http://localhost:3000

## Environment Variables

- `MONGO_HOST`: MongoDB host (default: localhost)
- `MONGO_PORT`: MongoDB port (default: 27017)
- `MONGO_USER`: MongoDB username
- `MONGO_PASS`: MongoDB password
- `MONGO_DB`: MongoDB database name (default: chronos)

## Pages

### `/` - Event Feed
Displays the last 50 events in real-time with:
- Event type and severity badges
- Sector information
- Autonomy level indicator
- Auto-refresh every 5 seconds

### `/map` - Sector Map
Grid view showing status of 3 sectors:
- Color-coded status (green/yellow/orange/red)
- Latest event summary
- Last updated timestamp
- Auto-refresh every 5 seconds

### `/audit` - Audit Decisions
List of all audit decisions with:
- Decision details (type, maker, action, outcome)
- Reasoning
- Computed Solana hash
- Auto-refresh every 10 seconds

## UI Features

- Dark mode theme
- Clean card-based layout
- Large status indicators
- Autonomy level badge
- Responsive design

## API Routes

- `/api/events`: Fetch recent events from MongoDB
- `/api/audit`: Fetch audit decision events
- `/api/sectors`: Fetch sector status information
