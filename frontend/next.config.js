/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "https://rankyflow-production.up.railway.app"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
