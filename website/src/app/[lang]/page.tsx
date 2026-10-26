import { notFound } from 'next/navigation';
import { Header } from '@/components/Header';
import { LOCALE_SEGMENT, localeFromSegment, messages } from '@/i18n';
import { getRepoStats } from '@/lib/github';
import { mediaMap, pickMedia } from '@/lib/media';
import { getScreenshots } from '@/lib/screenshots';
import { HERO_SHOTS, HOME_GALLERY, latestIsoUrl } from '@/lib/site';
import { BadgeBar } from '@/sections/BadgeBar';
import { Faq } from '@/sections/Faq';
import { Features } from '@/sections/Features';
import { Footer } from '@/sections/Footer';
import { Gallery } from '@/sections/Gallery';
import { Hero } from '@/sections/Hero';
import { KeyFacts } from '@/sections/KeyFacts';
import { OpenSource } from '@/sections/OpenSource';
import { Support } from '@/sections/Support';

// Estrelas, forks e release do GitHub revalidados a cada hora (ISR).
export const revalidate = 3600;

// A home resume: telas primeiro, depois os recursos (cada um leva à sua
// página) e o que convém saber antes de baixar.
export default async function Home({ params }: PageProps<'/[lang]'>) {
  const locale = localeFromSegment((await params).lang);
  if (!locale) notFound();
  const stats = await getRepoStats();
  const media = mediaMap(getScreenshots(), messages[locale].shots, LOCALE_SEGMENT[locale]);
  const gallery = HOME_GALLERY.map(({ page, shots }) => ({ page, items: pickMedia(media, shots) })).filter((g) => g.items.length);
  return (
    <>
      <Header />
      <div className="lg:pl-64">
      <main id="main">
        <Hero slides={pickMedia(media, HERO_SHOTS)} downloadUrl={stats?.release?.iso ?? latestIsoUrl()} />
        <BadgeBar />
        <Gallery groups={gallery} />
        <Features />
        <KeyFacts />
        <OpenSource stats={stats} />
        <Faq />
        <Support />
      </main>
      <Footer />
      </div>
    </>
  );
}
