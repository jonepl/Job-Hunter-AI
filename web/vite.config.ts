import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI backend (uvicorn on :8000) so the
// SPA and API share an origin in development, mirroring the same-origin prod
// deployment where FastAPI serves the built SPA.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
