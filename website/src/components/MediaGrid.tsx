'use client';

import { useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import { Lightbox } from './Lightbox';
import { ScreenThumb } from './ScreenThumb';

// Uma grade de telas com legenda curta; o clique abre o lightbox da grade.
export function MediaGrid({ items, className = 'grid-cols-2 lg:grid-cols-4' }: { items: Media[]; className?: string }) {
  const { t } = useI18n();
  const [open, setOpen] = useState<number | null>(null);
  return (
    <>
      <ul className={`grid gap-4 ${className}`}>
        {items.map((m, i) => (
          <li key={m.id}>
            <figure>
              <ScreenThumb
                media={m}
                onOpen={() => setOpen(i)}
                openLabel={t.hero.carousel.open}
                animatedLabel={t.gallery.animated}
                sizes="(min-width: 1024px) 280px, 46vw"
              />
              <figcaption className="mt-2.5 px-1">
                <span className="block text-sm font-semibold text-fg">{m.title}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-muted">{m.caption}</span>
              </figcaption>
            </figure>
          </li>
        ))}
      </ul>
      <Lightbox items={items} index={open} onIndex={setOpen} labels={t.hero.carousel} />
    </>
  );
}
