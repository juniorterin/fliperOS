'use client';

import { useState } from 'react';
import { Lightbox } from '@/components/Lightbox';
import { Reveal } from '@/components/Reveal';
import { ScreenThumb } from '@/components/ScreenThumb';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';

// A faixa de telas da home: poucas e variadas, que rolam para o lado. O resto
// das telas está no fim de cada página.
export function Gallery({ items }: { items: Media[] }) {
  const { t } = useI18n();
  const g = t.gallery;
  const [open, setOpen] = useState<number | null>(null);
  return (
    <section id="screenshots" aria-labelledby="screenshots-title" className="relative py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="screenshots" kicker={g.kicker} title={g.title} intro={g.intro} />
        <Reveal>
          <ul className="-mx-4 mt-10 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-5 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
            {items.map((m, i) => (
              <li key={m.id} className="w-[72vw] shrink-0 snap-start sm:w-64">
                <figure>
                  <ScreenThumb media={m} onOpen={() => setOpen(i)} openLabel={t.hero.carousel.open} animatedLabel={g.animated} sizes="260px" />
                  <figcaption className="mt-2.5 px-1">
                    <span className="block text-sm font-semibold text-fg">{m.title}</span>
                    <span className="mt-0.5 block text-xs leading-relaxed text-muted">{m.caption}</span>
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </Reveal>
        <p className="mt-2 font-mono text-xs text-comment">{g.seeAll}</p>
        <Lightbox items={items} index={open} onIndex={setOpen} labels={t.hero.carousel} />
      </div>
    </section>
  );
}
