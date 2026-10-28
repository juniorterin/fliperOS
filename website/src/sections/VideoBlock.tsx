'use client';

import { Play } from 'lucide-react';
import { useState } from 'react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { TubeShot } from '@/components/TubeShot';
import { useI18n } from '@/i18n/I18nProvider';
import { track } from '@/lib/analytics';
import type { Media } from '@/lib/media';
import { LINKS, VIDEO_ID } from '@/lib/site';

// O vídeo de apresentação. O player do YouTube só carrega ao clicar (domínio
// sem cookies), então a home não paga o peso dele nem cria cookie antes do aceite.
export function VideoBlock({ cover }: { cover?: Media }) {
  const { t } = useI18n();
  const v = t.video;
  const [playing, setPlaying] = useState(false);
  return (
    <section id="video" aria-labelledby="video-title" className="relative py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="video" kicker={v.kicker} title={v.title} />
        <Reveal className="mt-14 grid items-center gap-8 lg:grid-cols-[1.4fr_1fr] lg:gap-12">
          <div className="crt-bezel rounded-2xl p-2 sm:p-3">
            <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-bg-deeper">
              {playing ? (
                <iframe
                  title={v.frameTitle}
                  src={`https://www.youtube-nocookie.com/embed/${VIDEO_ID}?autoplay=1&rel=0`}
                  allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                  allowFullScreen
                  className="absolute inset-0 size-full"
                />
              ) : (
                <button
                  type="button"
                  aria-label={v.play}
                  onClick={() => {
                    track('video_play', { video: VIDEO_ID });
                    setPlaying(true);
                  }}
                  className="group absolute inset-0 grid place-items-center"
                >
                  {cover ? (
                    <span className="absolute inset-0 flex items-center justify-center bg-bg-deeper">
                      <span className="aspect-[4/3] h-full">
                        <TubeShot media={cover} sizes="(min-width: 1024px) 640px, 92vw" className="size-full rounded-none bg-transparent p-0 shadow-none" />
                      </span>
                    </span>
                  ) : null}
                  <span className="relative grid size-20 place-items-center rounded-full bg-pink pl-1 text-bg-deeper shadow-[0_0_0_10px,0_20px_50px_-10px] shadow-pink/25 transition group-hover:scale-105">
                    <Play className="size-8 fill-current" aria-hidden="true" />
                  </span>
                </button>
              )}
            </div>
          </div>
          <div>
            <p className="text-lg leading-relaxed text-muted">{v.text}</p>
            <ul className="mt-5 grid gap-2.5">
              {v.points.map((p) => (
                <li key={p} className="relative pl-5 text-muted before:absolute before:left-0 before:font-mono before:text-green before:content-['>']">
                  {p}
                </li>
              ))}
            </ul>
            <a
              href={LINKS.video}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-6 inline-block font-mono text-sm text-cyan transition-colors hover:text-fg"
            >
              {v.youtube}
              <span className="sr-only">{t.a11y.external}</span>
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
