import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Playwright and some CI healthchecks use 127.0.0.1; Next 16 blocks that host by default.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/block/:id",
          destination: "/block",
        },
        {
          source: "/tx/:id",
          destination: "/tx",
        },
        {
          source: "/address/:id",
          destination: "/address",
        },
        {
          source: "/:network/block/:id",
          destination: "/:network/block",
        },
        {
          source: "/:network/tx/:id",
          destination: "/:network/tx",
        },
        {
          source: "/:network/address/:id",
          destination: "/:network/address",
        },
        {
          source: "/api/:path*",
          destination: "http://127.0.0.1:8080/api/:path*",
        },
        {
          source: "/healthz",
          destination: "http://127.0.0.1:8080/healthz",
        },
      ],
    };
  },
};

export default nextConfig;
