# Frontend Client

This directory contains the frontend application built with Vite.

## Structure

```
client/
├── src/
│   ├── main.js              # Main application entry point
│   ├── data_models.js       # Frontend data validation models
│   ├── styles/
│   │   └── main.css         # Main stylesheet with Tailwind CSS
│   └── widgets/             # Widget components (to be moved)
├── index.html               # Main HTML template
└── README.md               # This file
```

## Development

### Prerequisites

- Node.js 18+ installed
- Dependencies installed: `npm install`

### Development Server

Start the Vite development server:

```bash
npm run dev
```

This will start the frontend on `http://localhost:3000` with:
- Hot Module Replacement (HMR)
- API proxy to backend (`http://localhost:8000`)
- Source maps for debugging

### Building for Production

Build the frontend for production:

```bash
npm run build
```

This will:
- Bundle and minify all assets
- Output to `../public/` directory
- Generate optimized CSS and JavaScript

### Preview Production Build

Preview the production build locally:

```bash
npm run preview
```

## Integration with Backend

The frontend is designed to work with the Python FastAPI backend:

1. **Development**: Vite dev server proxies API calls to `http://localhost:8000`
2. **Production**: Built assets are served by the FastAPI server from `/public/`

## Dependencies

- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Font Awesome**: Icon library
- **Chart.js**: Charting library
- **Preline**: UI component library

## Configuration

- `vite.config.js`: Vite configuration
- `tailwind.config.js`: Tailwind CSS configuration
- `postcss.config.js`: PostCSS configuration

## Workflow

1. **Development**: Run `make dev-frontend` for frontend, `make dev-server` for backend
2. **Production**: Run `make server` to build frontend and start backend
3. **Hot Reload**: Changes to frontend files will automatically reload in development 