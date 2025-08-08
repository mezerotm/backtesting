# Vite + FastAPI Monorepo Setup

This document explains the modern monorepo architecture for the GreenArrow Labs application, combining Vue.js frontend with FastAPI backend.

## 🏗️ Architecture Overview

### Development Mode
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Vite)        │    │   (FastAPI)     │    │   (PocketBase)  │
│   Port 3001     │◄──►│   Port 8000     │    │   Port 8090     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Production Mode
```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                          │
│                    Port 8000                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   API       │  │   Static    │  │   SPA Routing       │ │
│  │ Endpoints   │  │   Files     │  │   (Vue Router)      │ │
│  │ /api/*      │  │ /static/*   │  │   /* -> index.html  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
backtesting/
├── client/                 # Frontend source code
│   ├── src/               # Vue.js source files
│   ├── index.html         # Development entry point
│   └── vite.config.ts     # Vite configuration
├── server/                # Backend source code
│   ├── api/               # FastAPI endpoints
│   └── main.py            # Server entry point
├── public/                # Production build output
│   ├── index.html         # Production entry point
│   ├── js/                # Built JavaScript files
│   ├── css/               # Built CSS files
│   └── assets/            # Built assets (images, etc.)
├── assets/                # Source assets (not served)
├── package.json           # Node.js dependencies
└── requirements.txt       # Python dependencies
```

## 🚀 Development Workflow

### Starting Development Environment

1. **Start the database** (Terminal 1):
   ```bash
   make db-start
   ```

2. **Start the backend API** (Terminal 2):
   ```bash
   make dev-server
   ```

3. **Start the frontend dev server** (Terminal 3):
   ```bash
   make dev-frontend
   ```

### Development URLs
- **Frontend**: http://localhost:3001 (Vite dev server)
- **Backend API**: http://localhost:8000 (FastAPI)
- **API Docs**: http://localhost:8000/docs
- **Database**: http://127.0.0.1:8090/_/

## 🏭 Production Build

### Building for Production
```bash
# Build frontend assets
make build-frontend

# Start production server
make server
```

### Production URLs
- **Application**: http://localhost:8000 (FastAPI serves everything)
- **API Docs**: http://localhost:8000/docs
- **Database**: http://127.0.0.1:8090/_/

## 🔧 Configuration Details

### Vite Configuration (`client/vite.config.ts`)
- **Development**: Serves from `client/src/` with hot reload
- **Production**: Builds to `public/` with hashed filenames
- **API Proxy**: Forwards `/api/*` to FastAPI backend
- **Asset Organization**: 
  - JS files → `public/js/[name].[hash].js`
  - CSS files → `public/css/[name].[hash].css`
  - Assets → `public/assets/[name].[hash].[ext]`

### FastAPI Configuration (`server/api/main.py`)
- **Development**: Only serves API endpoints
- **Production**: Serves API + static files + SPA routing
- **Security**: Only serves from `public/` directory
- **SPA Support**: All non-API routes serve `index.html` for Vue Router

## 🛡️ Security Best Practices

### Static File Serving
✅ **SAFE** - Only serve from `public/` directory
❌ **UNSAFE** - Never serve from source directories:
- `server/` (API source code)
- `utils/` (utility modules)
- `strategies/` (trading strategies)
- `workflows/` (workflow code)
- `libs/` (libraries)
- `logs/` (sensitive logs)
- `client/` (frontend source)
- `assets/` (source assets)

### Environment Variables
```bash
ENV=development          # or production
POLYGON_API_KEY=xxx      # Market data API
FRED_API_KEY=xxx         # Economic data API
OPENAI_API_KEY=xxx       # AI explanations
```

## 🔄 Build Process

### Development
1. Vite dev server watches `client/src/`
2. FastAPI serves only API endpoints
3. API proxy forwards requests to backend
4. Hot reload for both frontend and backend

### Production
1. Vite builds assets to `public/`
2. FastAPI serves everything from single port
3. SPA routing handles client-side navigation
4. Static files served with proper caching

## 📦 Key Commands

```bash
# Development
make dev-server          # Backend with hot reload
make dev-frontend        # Frontend with hot reload
make dev                 # Show development setup

# Production
make build-frontend      # Build frontend assets
make server              # Start production server

# Database
make db-start            # Start PocketBase
make db-init             # Initialize database

# Maintenance
make clean               # Clean build artifacts
make syntax-check        # Format Python code
```

## 🎯 Benefits of This Setup

1. **Clear Separation**: Development vs production modes
2. **Hot Reload**: Fast development iteration
3. **Single Server**: Production simplicity
4. **Security**: Proper static file serving
5. **SPA Support**: Client-side routing
6. **Asset Optimization**: Hashed filenames for caching
7. **Monorepo**: Single repository, multiple concerns

## 🔍 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3001, 8000, 8090 are available
2. **Build errors**: Run `make clean` then `make build-frontend`
3. **API proxy issues**: Check that backend is running on port 8000
4. **Static file 404s**: Verify files are in `public/` directory

### Debug Commands
```bash
# Check running processes
lsof -i :3001
lsof -i :8000
lsof -i :8090

# View logs
tail -f logs/server.log
tail -f logs/api/*.log
``` 