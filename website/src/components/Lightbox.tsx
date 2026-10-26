'use client';

import Image from 'next/image';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { track } from '@/lib/analytics';
import type { Media } from '@/lib/media';

export type LightboxLabels = { previous: string; next: string; close: string };

// A tela ampliada de uma galeria: setas trocam, Esc ou um clique fora fecha.
export function Lightbox({
  items,
  index,
  onIndex,
  labels,
}: {
  items: Media[];
  index: number | null;
  onIndex: (index: number | null) => void;
  labels: LightboxLabels;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const item = index === null ? null : items[index];

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (item && !dialog.open) dialog.showModal();
    if (!item && dialog.open) dialog.close();
  }, [item]);

  useEffect(() => {
    if (item) track('screenshot_view', { screenshot: item.id });
  }, [item]);

  const go = (step: 1 | -1) => {
    if (index === null) return;
    onIndex((index + step + items.length) % items.length);
  };

  return (
    <dialog
      ref={ref}
      aria-label={item?.title}
      className="m-auto w-[min(1200px,94vw)] max-w-none rounded-2xl border border-line bg-bg-deeper p-0 text-fg"
      onClick={(e) => e.target === e.currentTarget && onIndex(null)}
      onClose={() => onIndex(null)}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight') go(1);
        if (e.key === 'ArrowLeft') go(-1);
      }}
    >
      {item ? (
        <div>
          <div className="relative aspect-[4/3] w-full bg-black sm:aspect-[16/10]">
            <Image
              src={item.src}
              alt={item.alt}
              fill
              sizes="94vw"
              unoptimized
              className={`object-contain ${item.pixelated ? '[image-rendering:pixelated]' : ''}`}
            />
          </div>
          <div className="flex items-center gap-3 border-t border-line px-4 py-3 sm:px-5">
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{item.title}</p>
              <p className="truncate text-sm text-muted">{item.caption}</p>
            </div>
            {items.length > 1 ? (
              <>
                <button type="button" onClick={() => go(-1)} aria-label={labels.previous} className="rounded-lg border border-line p-2 hover:border-purple">
                  <ChevronLeft className="size-5" aria-hidden="true" />
                </button>
                <button type="button" onClick={() => go(1)} aria-label={labels.next} className="rounded-lg border border-line p-2 hover:border-purple">
                  <ChevronRight className="size-5" aria-hidden="true" />
                </button>
              </>
            ) : null}
            <button
              type="button"
              onClick={() => onIndex(null)}
              aria-label={labels.close}
              className="rounded-lg border border-line p-2 hover:border-pink"
              autoFocus
            >
              <X className="size-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      ) : null}
    </dialog>
  );
}
