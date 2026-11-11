import type { NextConfig } from "next";

const apiProxyTarget = process.env.CFIP_API_PROXY_TARGET ?? "http://127.0.0.1:43124";
const staticExport = process.env.CFIP_STATIC_EXPORT === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  ...(staticExport
    ? {
        output: "export" as const,
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {}),
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

if (!staticExport) {
  nextConfig.rewrites = async () => [
    {
      source: "/cfip-api/:path*",
      destination: `${apiProxyTarget}/:path*`,
    },
  ];
}

export default nextConfig;
