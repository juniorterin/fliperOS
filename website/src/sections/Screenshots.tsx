'use client';

import Image from 'next/image';
import { ChevronLeft, ChevronRight, ImagePlus, Maximize2, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { track } from '@/lib/analytics';
import type { ScreenshotMap } from '@/lib/screenshots';

export function Screenshots({ screenshots }: { screenshots: ScreenshotMap }) {
  const { t } = useI18n();
  const s = t.screenshots;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [current, setCurrent] = useState<number | null>(null);

  const available = s.items.filter((item) => screenshots[item.id]);

  const open = (id: string) => {
    setCurrent(available.findIndex((item) => item.id === id));
    dialogRef.current?.showModal();
  };

  const step = useCallback(
    (delta: number) => setCurrent((i) => (i === null ? i : (i + delta + available.length) % available.length)),
    [available.length],
  );

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') step(1);
      if (e.key === 'ArrowLeft') step(-1);
    };
    const onClose = () => setCurrent(null);
    dialog.addEventListener('keydown', onKey);
    dialog.addEventListener('close', onClose);
    return () => {
      dialog.removeEventListener('keydown', onKey);
      dialog.removeEventListener('close', onClose);
    };
  }, [step]);

  const shown = current !== null ? available[current] : null;

  useEffect(() => {
    if (shown) track('screenshot_view', { screenshot: shown.id });
  }, [shown]);
  const shownSrc = shown ? screenshots[shown.id] : null;

  return (
    <section id="screenshots" aria-labelledby="screenshots-title" className="relative bg-bg-deeper/40 py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-purple/50 to-transparent" />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="screenshots" kicker={s.kicker} title={s.title} intro={s.intro} />

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:gap-5">
          {s.items.map((item, i) => {
            const src = screenshots[item.id];
            return (
              <Reveal as="li" key={item.id} delay={i * 50}>
                <figure className="card group flex h-full flex-col overflow-hidden rounded-2xl">
                  <div
                    className={`relative w-full ${src ? 'overflow-hidden bg-bg' : 'crt-screen rounded-none'}  aspect-[4/3]`}
                  >
                    {src ? (
                      <button
                        type="button"
                        onClick={() => open(item.id)}
                        className="absolute inset-0 z-[4] block h-full w-full cursor-zoom-in"
                        aria-label={`${s.open}: ${item.title}`}
                      >
                        <Image
                          src={src}
                          alt={item.caption}
                          fill
                          loading="lazy"
                          sizes="(min-width: 640px) 50vw, 100vw"
                          unoptimized
                          className="object-contain transition duration-500 group-hover:scale-[1.02]"
                        />
                        <span className="absolute top-3 right-3 rounded-lg bg-bg-deeper/80 p-2 text-fg opacity-80 transition group-hover:opacity-100">
                          <Maximize2 className="size-4" aria-hidden="true" />
                        </span>
                      </button>
                    ) : (
                      <div className="absolute inset-0 z-[1] flex flex-col items-center justify-center gap-3 border border-dashed border-line/80 p-5 text-center">
                        <ImagePlus className="size-8 text-comment" aria-hidden="true" />
                        <p className="font-mono text-xs tracking-wider text-muted uppercase">{s.pending}</p>
                        <p className="font-mono text-[11px] text-comment">
                          {s.expectedAt}
                          <br />
                          <code className="mt-1 inline-block rounded bg-bg-deeper/80 px-2 py-0.5 text-cyan">
                            /public/screenshots/{item.id}.webp
                          </code>
                        </p>
                      </div>
                    )}
                  </div>
                  <figcaption className="border-t border-line/60 px-5 py-4">
                    <p className="font-semibold text-fg">{item.title}</p>
                    <p className="mt-1 text-sm text-muted">{item.caption}</p>
                  </figcaption>
                </figure>
              </Reveal>
            );
          })}
        </ul>
      </div>

      <dialog
        ref={dialogRef}
        aria-label={shown?.title ?? s.title}
        className="m-auto w-[min(1200px,94vw)] max-w-none rounded-2xl border border-line bg-bg-deeper p-0 text-fg"
        onClick={(e) => e.target === e.currentTarget && dialogRef.current?.close()}
      >
        {shown && shownSrc ? (
          <figure>
            <div className="relative aspect-[4/3] w-full bg-black sm:aspect-[16/10]">
              <Image src={shownSrc} alt={shown.caption} fill sizes="94vw" unoptimized className="object-contain" />
            </div>
            <figcaption className="flex items-center gap-3 border-t border-line px-4 py-3 sm:px-5">
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{shown.title}</p>
                <p className="truncate text-sm text-muted">{shown.caption}</p>
              </div>
              {available.length > 1 ? (
                <>
                  <button type="button" onClick={() => step(-1)} aria-label={s.previous} className="rounded-lg border border-line p-2 hover:border-purple">
                    <ChevronLeft className="size-5" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => step(1)} aria-label={s.next} className="rounded-lg border border-line p-2 hover:border-purple">
                    <ChevronRight className="size-5" aria-hidden="true" />
                  </button>
                </>
              ) : null}
              <button
                type="button"
                onClick={() => dialogRef.current?.close()}
                aria-label={s.close}
                className="rounded-lg border border-line p-2 hover:border-pink"
                autoFocus
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </figcaption>
          </figure>
        ) : null}
      </dialog>
    </section>
  );
}
