/** @type {import('next').NextConfig} */
const DEFAULT_API_BASE_URL = 'http://localhost:8000';

const trimTrailingSlash = (value) => value.replace(/\/+$/, '');

const apiBaseUrl = trimTrailingSlash(
  process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    DEFAULT_API_BASE_URL,
);

const nextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
