import type { NextConfig } from "next";

// URL del backend FastAPI. El navegador solo habla con /backend/* (mismo origen),
// asi que no hace falta configurar CORS en el API.
const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/backend/:path*", destination: `${API_URL}/api/v1/:path*` },
      { source: "/comparison-data/:path*", destination: `${API_URL}/comparison-data/:path*` },
    ];
  },
  experimental: {
    agentFeedback: true,
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
