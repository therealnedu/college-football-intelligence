import type { NextConfig } from "next";

const apiProxyTarget = process.env.CFIP_API_PROXY_TARGET ?? "http://127.0.0.1:43124";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/cfip-api/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
