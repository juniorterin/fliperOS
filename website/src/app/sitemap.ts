import type { MetadataRoute } from 'next';
import { LOCALES, pagePath } from '@/i18n';
import { PAGE_SLUGS, SITE_URL } from '@/lib/site';

// A home e cada página de detalhe, nos dois idiomas, com os alternates de cada uma.
export default function sitemap(): MetadataRoute.Sitemap {
  return [undefined, ...PAGE_SLUGS].flatMap((page) => {
    const languages = {
      ...Object.fromEntries(LOCALES.map((l) => [l, `${SITE_URL}${pagePath(l, page)}`])),
      'x-default': page ? `${SITE_URL}${pagePath('en-US', page)}` : `${SITE_URL}/`,
    };
    return LOCALES.map((l) => ({
      url: `${SITE_URL}${pagePath(l, page)}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: page ? 0.8 : 1,
      alternates: { languages },
    }));
  });
}
