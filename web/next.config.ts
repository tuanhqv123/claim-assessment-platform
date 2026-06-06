import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle (.next/standalone) for a slim Docker
  // runtime image — no node_modules copy needed.
  output: "standalone",
};

export default nextConfig;
