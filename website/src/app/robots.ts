import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/site';

// Os robôs de busca das IAs (ChatGPT, Claude, Perplexity, Gemini) nomeados um
// a um: o "*" já os deixa entrar, mas alguns só seguem a regra com o nome deles.
const AI_BOTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'PerplexityBot', 'Google-Extended'];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: '*', allow: '/' }, { userAgent: AI_BOTS, allow: '/' }],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
