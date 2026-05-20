import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "src/main/frontend",
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:5001",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
