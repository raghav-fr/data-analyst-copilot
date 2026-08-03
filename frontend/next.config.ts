import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "data-analyst-copilot.onrender.com",
        port: "",
      },
    ],
    dangerouslyAllowSVG: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://data-analyst-copilot.onrender.com/api/:path*",
      },
      {
        source: "/outputs/:path*",
        destination: "https://data-analyst-copilot.onrender.com/outputs/:path*",
      },
    ];
  },
  devIndicators: {
    // If you want to configure dev indicators, you can use the `position` property:
    // position: "bottom-right"
  },
};

export default nextConfig;
