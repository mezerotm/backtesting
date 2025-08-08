# Frontend Client

This directory contains the Vue.js 3 frontend application with TypeScript support.

## 🏗️ Architecture

```
client/
├── config/                 # Build and development configuration
│   ├── vite.config.ts     # Vite build configuration
│   ├── tsconfig.json      # TypeScript configuration
│   ├── tsconfig.node.json # TypeScript config for Node tools
│   └── .eslintrc.js       # ESLint configuration
├── src/                   # Source code
│   ├── components/        # Vue components
│   │   ├── pages/         # Page components
│   │   ├── widgets/       # Widget components
│   │   └── ui/           # Reusable UI components
│   ├── stores/           # Pinia state management
│   ├── types/            # TypeScript type definitions
│   ├── styles/           # CSS styles
│   └── vue-app.ts        # Application entry point
├── index.html            # HTML entry point
└── README.md             # This file
```

## 🚀 Development

### Prerequisites
- Node.js 18+
- npm or yarn

### Setup
```bash
# Install dependencies (from project root)
npm install

# Start development server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

## 🛠️ Technology Stack

- **Vue.js 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Pinia** - State management
- **Vue Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Fast build tool and dev server
- **ESLint** - Code linting

## 📁 Key Directories

### `src/components/`
- **pages/**: Route-level components (LandingPage, DashboardPage, etc.)
- **widgets/**: Feature-specific components (PortfolioWidget, etc.)
- **ui/**: Reusable UI components (ToastContainer, etc.)

### `src/stores/`
Pinia stores for state management:
- `auth.ts` - Authentication state
- `portfolio.ts` - Portfolio data
- `marketData.ts` - Market data and workflows
- `toast.ts` - Toast notifications

### `src/types/`
TypeScript type definitions for the application.

### `config/`
Build and development configuration files.

## 🔧 Configuration

All build configuration is contained in the `config/` directory:
- **vite.config.ts**: Vite build and dev server configuration
- **tsconfig.json**: TypeScript compiler options
- **.eslintrc.js**: Code linting rules

## 🎯 Features

- **Hot Module Replacement (HMR)** - Instant updates during development
- **Type Safety** - Full TypeScript support throughout
- **Component-Based Architecture** - Modular, reusable components
- **State Management** - Centralized state with Pinia
- **Routing** - Client-side routing with Vue Router
- **Responsive Design** - Mobile-first with Tailwind CSS 