import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Use standalone output only when building inside Docker (set NEXT_OUTPUT_MODE=standalone).
  // Vercel manages its own bundling and does not support this flag.
  ...(process.env.NEXT_OUTPUT_MODE === "standalone" ? { output: "standalone" } : {}),
};

export default nextConfig;
