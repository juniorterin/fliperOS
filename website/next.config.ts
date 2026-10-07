import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  experimental: {
    globalNotFound: true,
  },
  images: {
    formats: ['image/avif', 'image/webp'],
  },
};

export default nextConfig;
