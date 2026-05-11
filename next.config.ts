import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  serverExternalPackages: ["oracledb"],
  /**
   * 開発時に LAN IP で開くと、ブラウザの Origin が localhost と異なり、/_next 等へのリクエストが
   * ブロックされ Internal Server Error になることがある。許可するホスト名を列挙する。
   * @see https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins
   */
  allowedDevOrigins: ["192.168.3.180"],
};

export default nextConfig;
