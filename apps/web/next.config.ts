// next.config.ts — NextConfig type comes from next-env.d.ts when using `next build`
// or from our src/next-modules.d.ts when using plain `tsc --noEmit`
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
