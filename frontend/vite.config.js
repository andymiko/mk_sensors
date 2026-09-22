import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    base: env.VITE_BASE_PATH || "/",
    plugins: [vue()],
    optimizeDeps: {
      exclude: ["maplibre-gl"],
    },
    server: {
      port: Number(env.VITE_PORT || 5173),
      proxy: {
        "/api": {
          target: env.VITE_BACKEND_URL || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
