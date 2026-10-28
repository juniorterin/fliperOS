import { notFound } from 'next/navigation';
import { Header } from '@/components/Header';
import { LOCALE_SEGMENT, localeFromSegment, messages } from '@/i18n';
import { getRepoStats } from '@/lib/github';
import { mediaMap, pickMedia } from '@/lib/media';
import { getScreenshots } from '@/lib/screenshots';
import { HERO_SHOTS, HOME_HIGHLIGHTS, HOME_STEPS, HOME_STRIP, latestIsoUrl } from '@/lib/site';
import { BadgeBar } from '@/sections/BadgeBar';
import { Faq } from '@/sections/Faq';
import { Features } from '@/sections/Features';
import { Footer } from '@/sections/Footer';
import { Gallery } from '@/sections/Gallery';
import { Hero } from '@/sections/Hero';
import { Highlights } from '@/sections/Highlights';
import { HowItWorks } from '@/sections/HowItWorks';
import { KeyFacts } from '@/sections/KeyFacts';
import { OpenSource } from '@/sections/OpenSource';
import { Support } from '@/sections/Support';
import { VideoBlock } from '@/sections/VideoBlock';
import { WhatsNew } from '@/sections/WhatsNew';

// Estrelas, forks e release do GitHub revalidados a cada hora (ISR).
export const revalidate = 3600;

// A home resume: como funciona, os destaques, as novidades, o vídeo e uma
// faixa de telas; depois os recursos (cada um leva à sua página) e o que
// convém saber antes de baixar.
export default async function Home({ params }: PageProps<'/[lang]'>) {
  const locale = localeFromSegment((await params).lang);
  if (!locale) notFound();
  const stats = await getRepoStats();
  const lang = LOCALE_SEGMENT[locale];
  const media = mediaMap(getScreenshots(), messages[locale].shots, lang);
  const steps = HOME_STEPS.map(({ page, shot }) => ({ page, media: media[shot] }));
  const highlights = HOME_HIGHLIGHTS.map(({ id: key, page, shot, extra, since }) => ({
    id: key,
    page,
    since,
    media: media[shot],
    extra: extra ? media[extra] : undefined,
  }));
  return (
    <>
      <Header />
      <div className="lg:pl-64">
      <main id="main">
        <Hero slides={pickMedia(media, HERO_SHOTS)} downloadUrl={stats?.release?.iso ?? latestIsoUrl()} />
        <BadgeBar />
        <HowItWorks steps={steps} />
        <Highlights items={highlights} />
        <WhatsNew />
        <VideoBlock cover={media['anim/frontend-full']} />
        <Gallery items={pickMedia(media, HOME_STRIP)} />
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
