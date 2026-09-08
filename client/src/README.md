# Frontend Entry Point Structure

```
client/src/
├── vue-app.ts           # Entry point — creates Vue app, router, and Pinia store
├── main.ts              # (deprecated) Alternate entry point — not used
├── components/
│   ├── App.vue          # Root component — template with <router-view> + ToastContainer
│   ├── pages/           # Route-level page components
│   ├── ui/              # Shared UI components (toasts, tables, forms)
│   └── widgets/         # Dashboard widget components
├── stores/              # Pinia stores (auth, reports, widgets, etc.)
├── utils/               # Helper functions and composables
└── router/              # Route definitions (if extracted from vue-app.ts)
```

## Key files

- **`vue-app.ts`** — Creates and mounts the Vue app. Imports `App` from `./components/App.vue` (the real root component).
- **`components/App.vue`** — Root Vue component. Renders `<router-view>` and `<ToastContainer>`. Sets up auth check on mount.
- **`components/pages/`** — Page components for each route (DashboardPage, LandingPage, etc.).

## Notes

- The original empty `client/src/App.vue` was removed — it was a dead file (0 bytes). The real root component is at `components/App.vue`.
- `vue-app.ts` uses `createWebHistory()` for clean URLs (no hash). The server must redirect all routes to `index.html`.
- The build output goes to `client/dist/` (configured by `vite.config.ts`), which is then served by the backend.