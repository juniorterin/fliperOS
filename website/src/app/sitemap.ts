import type { MetadataRoute } from 'next';
import { LOCALES, localePath } from '@/i18n';
import { SITE_URL } from '@/lib/site';

const languages = {
  ...Object.fromEntries(LOCALES.map((l) => [l, `${SITE_URL}${localePath(l)}`])),
  'x-default': `${SITE_URL}/`,
};

export default function sitemap(): MetadataRoute.Sitemap {
  return LOCALES.map((l) => ({
    url: `${SITE_URL}${localePath(l)}`,
    lastModified: new Date(),
    changeFrequency: 'weekly',
    priority: 1,
    alternates: { languages },
  }));
}
