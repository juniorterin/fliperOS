'use client';

import { useState } from 'react';
import { Lightbox } from '@/components/Lightbox';
import { Reveal } from '@/components/Reveal';
import { ScreenThumb } from '@/components/ScreenThumb';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media, MediaMap } from '@/lib/media';
import type { PageSlug } from '@/lib/site';

// Os recursos de uma página, um por bloco: o texto de um lado e a tela do
// outro, trocando de lado a cada bloco. Sem tela, o bloco é só o texto.
export function FeatureRows({ page, media }: { page: PageSlug; media: MediaMap }) {
  const { t } = useI18n();
  const [open, setOpen] = useState<number | null>(null);
  const rows: { shot: string; title: string; text: string; points: string[] }[] = t.pages[page].rows;
  if (!rows.length) return null;
  const shown: Media[] = rows.flatMap((r) => (media[r.shot] ? [media[r.shot]] : []));
  let side = 0;
  return (
    <section className="relative pb-12 sm:pb-20">
      <div className="mx-auto grid max-w-7xl gap-16 px-4 sm:gap-24 sm:px-6 lg:px-8">
        {rows.map((row) => {
          const m = media[row.shot];
          const text = (
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-fg sm:text-3xl">{row.title}</h2>
              <p className="mt-4 text-lg leading-relaxed text-pretty text-muted">{row.text}</p>
              {row.points.length ? (
                <ul className="mt-5 flex flex-wrap gap-2">
                  {row.points.map((p) => (
                    <li key={p} className="rounded-md border border-line bg-bg-deeper/70 px-2.5 py-1 font-mono text-xs text-fg">
                      {p}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
          if (!m) {
            return (
              <Reveal key={row.title} className="card mx-auto w-full max-w-3xl rounded-2xl p-6 sm:p-8">
                {text}
              </Reveal>
            );
          }
          const flip = side++ % 2 === 1;
          return (
            <Reveal key={row.title} className="grid items-center gap-8 lg:grid-cols-2 lg:gap-14">
              <div className={flip ? 'lg:order-2' : ''}>
                <ScreenThumb
                  media={m}
                  large
                  onOpen={() => setOpen(shown.indexOf(m))}
                  openLabel={t.hero.carousel.open}
                  animatedLabel={t.gallery.animated}
                  sizes="(min-width: 1024px) 560px, 92vw"
                />
              </div>
              <div className={flip ? 'lg:order-1' : ''}>{text}</div>
            </Reveal>
          );
        })}
      </div>
      <Lightbox items={shown} index={open} onIndex={setOpen} labels={t.hero.carousel} />
    </section>
  );
}
