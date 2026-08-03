import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
    ],
    dangerouslyAllowSVG: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/outputs/:path*",
        destination: "http://localhost:8000/outputs/:path*",
      },
    ];
  },
  devIndicators: {
    // If you want to configure dev indicators, you can use the `position` property:
    // position: "bottom-right"
  },
};

export default nextConfig;
