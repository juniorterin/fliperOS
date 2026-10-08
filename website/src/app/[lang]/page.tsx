import { Header } from '@/components/Header';
import { getRepoStats } from '@/lib/github';
import { getScreenshots } from '@/lib/screenshots';
import { HERO_SCREENSHOT, latestIsoUrl } from '@/lib/site';
import { BadgeBar } from '@/sections/BadgeBar';
import { Crt } from '@/sections/Crt';
import { Emulators } from '@/sections/Emulators';
import { Features } from '@/sections/Features';
import { Footer } from '@/sections/Footer';
import { Hero } from '@/sections/Hero';
import { MultiMonitor } from '@/sections/MultiMonitor';
import { OpenSource } from '@/sections/OpenSource';
import { Screenshots } from '@/sections/Screenshots';
import { Setup } from '@/sections/Setup';
import { Support } from '@/sections/Support';

// Estrelas, forks e release do GitHub revalidados a cada hora (ISR).
export const revalidate = 3600;

export default async function Home() {
  const [stats, screenshots] = await Promise.all([getRepoStats(), Promise.resolve(getScreenshots())]);
  return (
    <>
      <Header />
      <main id="main">
        <Hero screenshot={screenshots[HERO_SCREENSHOT]} downloadUrl={stats?.release?.iso ?? latestIsoUrl()} />
        <BadgeBar />
        <Features />
        <Screenshots screenshots={screenshots} />
        <Emulators />
        <Crt />
        <MultiMonitor />
        <Setup />
        <OpenSource stats={stats} />
        <Support />
      </main>
      <Footer />
    </>
  );
}
