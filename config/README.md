# Configuration Management

This directory contains all configuration files for the application, organized by environment and component.

## 📁 Directory Structure

```
config/
├── backend/         # Backend configuration files
│   ├── __init__.py
│   └── settings.py  # Python configuration (moved from utils/config.py)
├── frontend/        # Frontend configuration files
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .eslintrc.js
├── shared/          # Shared configuration files
│   ├── .eslintrc.js
│   └── env.example  # Environment variables template
└── README.md        # This file
```

## 🎯 Configuration Types

### Backend (`backend/`)
- **settings.py**: Python configuration (environment variables, API keys, etc.)
- **__init__.py**: Package initialization and exports

### Frontend (`frontend/`)
- **Vite Configuration**: Build tool and dev server settings
- **TypeScript Configuration**: Type checking and compilation options
- **Tailwind CSS**: Utility-first CSS framework configuration
- **PostCSS**: CSS processing pipeline
- **ESLint**: Code linting rules

### Shared (`shared/`)
- **ESLint**: Common linting rules across frontend and backend
- **env.example**: Template for environment variables

## 🔧 Usage

### Backend Development
```python
# Import configuration in Python
from config.backend.settings import POLYGON_API_KEY, ENV, IS_PRODUCTION
```

### Frontend Development
```bash
# Start development server with custom config
npm run dev

# Build with custom config
npm run build

# Type checking
npm run type-check
```

## 📋 Guidelines

1. **Environment Separation**: Use different configs for dev, staging, prod
2. **Security**: Never commit sensitive data (API keys, passwords)
3. **Validation**: Validate configuration on startup
4. **Documentation**: Document all configuration options
5. **Defaults**: Provide sensible defaults for all settings

## 🚀 Environment Variables

Use environment variables for sensitive configuration. Copy `config/shared/env.example` to `config/shared/.env` and fill in your values:

```bash
# Environment Configuration
ENV=development

# API Configuration
VITE_API_URL=http://localhost:8000

# PocketBase Configuration
PB_EMAIL=admin@example.com
PB_PASSWORD=your_admin_password

# Polygon API Configuration
POLYGON_API_KEY=your_polygon_api_key_here

# FRED API Configuration
FRED_API_KEY=your_fred_api_key_here

# Trading Economics API Configuration
TRADING_ECON_API_KEY=your_trading_economics_api_key_here

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
VITE_APP_NAME=GreenArrow Labs Dashboard
```

## 🔄 Configuration Updates

When updating configuration:

1. Update the appropriate config file
2. Test the changes in development
3. Update documentation if needed
4. Deploy with proper environment variables

## 📝 Migration Notes

- **utils/config.py** has been moved to **config/backend/settings.py**
- All Python imports have been updated to use the new location
- Frontend configs are now consolidated in **config/frontend/**
- **.env** file has been moved to **config/shared/.env**
- Environment template is available in **config/shared/env.example**
- Vite and FastAPI are configured to load environment variables from **config/shared/.env** 