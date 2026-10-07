import type { MetadataRoute } from 'next';
import enUS from '@/i18n/en-US';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'FliperOS',
    short_name: 'FliperOS',
    description: enUS.meta.description,
    start_url: '/',
    display: 'standalone',
    background_color: '#21222c',
    theme_color: '#21222c',
    icons: [
      { src: '/icon.svg', type: 'image/svg+xml', sizes: 'any' },
      { src: '/apple-icon', type: 'image/png', sizes: '180x180' },
    ],
  };
}
