import { Header } from '@/components/Header';
import { getRepoStats } from '@/lib/github';
import { getScreenshots } from '@/lib/screenshots';
import { latestIsoUrl } from '@/lib/site';
import { BadgeBar } from '@/sections/BadgeBar';
import { Crt } from '@/sections/Crt';
import { Emulators } from '@/sections/Emulators';
import { Faq } from '@/sections/Faq';
import { Features } from '@/sections/Features';
import { Footer } from '@/sections/Footer';
import { Hero } from '@/sections/Hero';
import { MultiMonitor } from '@/sections/MultiMonitor';
import { OpenHardware } from '@/sections/OpenHardware';
import { OpenSource } from '@/sections/OpenSource';
import { Pixelcade } from '@/sections/Pixelcade';
import { Requirements } from '@/sections/Requirements';
import { Setup } from '@/sections/Setup';
import { Support } from '@/sections/Support';
import { WebPanel } from '@/sections/WebPanel';

// Estrelas, forks e release do GitHub revalidados a cada hora (ISR).
export const revalidate = 3600;

export default async function Home() {
  const [stats, screenshots] = await Promise.all([getRepoStats(), Promise.resolve(getScreenshots())]);
  return (
    <>
      <Header />
      <div className="lg:pl-64">
      <main id="main">
        <Hero screenshots={screenshots} downloadUrl={stats?.release?.iso ?? latestIsoUrl()} />
        <BadgeBar />
        <Features />
        <WebPanel />
        <Emulators />
        <Crt />
        <MultiMonitor />
        <Pixelcade />
        <OpenHardware />
        <Setup />
        <Requirements />
        <OpenSource stats={stats} />
        <Faq />
        <Support />
      </main>
      <Footer />
      </div>
    </>
  );
}
