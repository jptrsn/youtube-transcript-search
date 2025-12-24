# YouTube Transcript Search

A full-stack application for searching YouTube video transcripts across channels. Automatically captures and indexes video transcripts, enabling fast search across entire channels or individual videos.

## Project Structure
```
.
├── api/                    # FastAPI backend
├── extension/              # Browser extension (Chrome & Firefox)
├── frontend/              # SvelteKit web interface
└── README.md
```

## Features

- **Automatic Transcript Capture**: Browser extension automatically extracts and submits YouTube transcripts
- **Cross-Channel Search**: Search across all indexed channels and videos
- **Dual Search Modes**:
  - In-page search UI injected directly into YouTube
  - Popup search with click-to-seek functionality
- **Real-time Updates**: WebSub integration for automatic transcript updates
- **Multi-browser Support**: Chrome and Firefox extensions with separate dev/prod builds

## Tech Stack

### Backend (API)
- FastAPI
- PostgreSQL
- SQLAlchemy ORM
- WebSub (PubSubHubbub) for YouTube notifications

### Frontend
- SvelteKit
- TypeScript

### Extension
- TypeScript
- Webpack
- Chrome & Firefox Manifest V3

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Chrome or Firefox browser

## Setup

### 1. Environment Configuration

Create `.env` files in the root directory:

**`.env` (development)**:
```bash
# Database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=youtube_transcripts
DB_HOST=localhost

# API
YOUTUBE_API_KEY=your_youtube_api_key
FRONTEND_ORIGIN=http://localhost:5173
WEBSUB_CALLBACK_URL=http://your-domain.com/webhooks/youtube
WEBSUB_SECRET=your_websub_secret

# Extension
PUBLIC_API_URL=http://localhost:8000
PUBLIC_CHROME_EXTENSION_ID=your_chrome_dev_extension_id
PUBLIC_FIREFOX_EXTENSION_ID=your_firefox_dev_extension_id
```

**`.env.prod` (production)**:
```bash
# Database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=youtube_transcripts
DB_HOST=your_production_host

# API
YOUTUBE_API_KEY=your_youtube_api_key
FRONTEND_ORIGIN=https://ytscri.be
WEBSUB_CALLBACK_URL=https://ytscri.be/webhooks/youtube
WEBSUB_SECRET=your_websub_secret

# Extension
PUBLIC_API_URL=https://ytscri.be
PUBLIC_CHROME_EXTENSION_ID=your_chrome_prod_extension_id
PUBLIC_FIREFOX_EXTENSION_ID=your_firefox_prod_extension_id
```

### 2. Backend Setup
```bash
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn api:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Extension Setup
```bash
cd extension

# Install dependencies
npm install

# Build for development
npm run build:chrome:dev
# or
npm run build:firefox:dev
```

#### Loading the Extension

**Chrome**:
1. Navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension/dist` folder

**Firefox**:
1. Navigate to `about:debugging`
2. Click "This Firefox"
3. Click "Load Temporary Add-on"
4. Select `extension/dist/manifest.json`

## Extension Build Commands
```bash
# Chrome
npm run build:chrome:dev      # Development build
npm run build:chrome:prod     # Production build (creates .zip)

# Firefox
npm run build:firefox:dev     # Development build
npm run build:firefox:prod    # Production build (creates .zip)

# Watch mode (Chrome dev)
npm run dev
```

## Extension Architecture

### Manifest Patching System

The extension uses a modular manifest patch system for different browsers and environments:

- `manifest.json` - Base manifest (development defaults)
- `manifest.chrome.dev.patch.json` - Chrome development overrides
- `manifest.chrome.prod.patch.json` - Chrome production overrides
- `manifest.firefox.dev.patch.json` - Firefox development overrides
- `manifest.firefox.prod.patch.json` - Firefox production overrides

### Search Modes

**Mode 1: Popup Search**
- Search via extension popup
- Results fetched from API
- Click result to seek video
- Transcript cached in service worker (50 video limit, FIFO)

**Mode 2: In-Page Search**
- Search UI injected into YouTube transcript panel
- DOM-based search with highlighting
- Keyboard navigation between matches
- Matches YouTube's native UI theme

## API Endpoints
```
GET  /api/channels                          # List all channels
GET  /api/channels/{channel_id}             # Get channel details
GET  /api/channels/{channel_id}/videos      # List channel videos
GET  /api/videos/{video_id}/exists          # Check if video exists
GET  /api/videos/{video_id}/details         # Get video with transcript
POST /api/videos/submit                     # Submit new video/transcript
POST /api/search                            # Search across transcripts
```

## API Documentation

FastAPI provides automatic interactive documentation via Swagger UI and ReDoc.

### Development
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

### Production
API documentation is disabled in production for security. To generate static documentation:
```bash
cd api
python scripts/export_openapi.py > api-docs.json
```

### Main Dependencies

**Backend:**
- FastAPI 0.104.1 - Web framework
- SQLAlchemy 2.0.23 - ORM
- Alembic 1.12.1 - Database migrations
- psycopg2-binary 2.9.9 - PostgreSQL adapter
- google-api-python-client 2.108.0 - YouTube API
- youtube-transcript-api 1.2.3 - Transcript extraction
- feedparser 6.0.11+ - RSS/Atom feed parsing
- APScheduler 3.10.4+ - Background job scheduling
- websockets 12.0 - WebSocket support
- fabric 3.0.0+ - SSH automation

**Frontend:**
- SvelteKit 2.48.5+ - Full-stack framework
- Vite 7.2.2+ - Build tool
- TypeScript 5.9.3+ - Type safety

**Extension:**
- TypeScript 5.9.3 - Language
- Webpack 5.103.0 - Bundler
- Chrome Types 0.1.31 - Extension API types

## Database Schema

- `channels` - YouTube channel metadata
- `videos` - Video information and metadata
- `transcripts` - Parsed transcript data with timestamps
- `websub_subscriptions` - Active WebSub subscriptions

## Database Migrations

The project uses Alembic for database schema management.

### Initial Setup
```bash
cd api

# Verify alembic.ini is configured
cat alembic.ini

# Run existing migrations
alembic upgrade head
```

### Creating New Migrations
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/
# Edit if needed, then apply
alembic upgrade head
```

### Common Migration Commands
```bash
# Check current version
alembic current

# View migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

## Development Notes

### Extension IDs

Chrome extension IDs are derived from public keys and are consistent across builds when using the production manifest patch. Development builds use auto-generated IDs based on the unpacked extension path.

Firefox extension IDs are specified in the `browser_specific_settings` section of the manifest.

### CORS Configuration

The API is configured to allow requests from:
- Frontend origin (localhost:5173 in dev, ytscri.be in prod)
- Chrome extension (via `chrome-extension://` protocol)
- Firefox extension (via `moz-extension://` protocol)

### (In)Security

- Private keys (`.pem` files) are gitignored
- Environment files containing secrets are gitignored
- Public keys in manifests are safe to commit
- Extension IDs are safe to commit (will be public once published)

## Deployment

### Backend

The API can be deployed to any Python hosting service that supports FastAPI. Ensure PostgreSQL is accessible and environment variables are configured.

### Frontend

Deploy the SvelteKit application to Vercel, Netlify, or any Node.js hosting platform.

### Extension

**Chrome Web Store**:
1. Build production version: `npm run build:chrome:prod`
2. Upload `youtube-transcript-search-chrome.zip` to Chrome Web Store Developer Dashboard

**Firefox Add-ons**:
1. Build production version: `npm run build:firefox:prod`
2. Upload `youtube-transcript-search-firefox.zip` to addons.mozilla.org

