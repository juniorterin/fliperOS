'use client';

import Image from 'next/image';
import { Play } from 'lucide-react';
import type { Media } from '@/lib/media';

// Uma tela numa moldura de tubo, que abre ampliada ao clicar.
export function ScreenThumb({
  media,
  onOpen,
  openLabel,
  animatedLabel,
  sizes,
  large = false,
}: {
  media: Media;
  onOpen: () => void;
  openLabel: string;
  animatedLabel: string;
  sizes: string;
  large?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`${openLabel}: ${media.title}`}
      className={`crt-bezel group block w-full cursor-zoom-in text-left transition hover:-translate-y-0.5 ${
        large ? 'rounded-[28px] p-4 sm:p-5' : 'rounded-2xl p-2.5'
      }`}
    >
      <span className={`relative block aspect-[4/3] w-full overflow-hidden bg-bg-deeper ${large ? 'rounded-[14px]' : 'rounded-lg'}`}>
        <Image
          src={media.src}
          alt={media.alt}
          fill
          sizes={sizes}
          unoptimized
          className={`object-contain ${media.pixelated ? '[image-rendering:pixelated]' : ''}`}
        />
        {media.animated ? (
          <span className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-md bg-bg-deeper/85 px-1.5 py-0.5 font-mono text-[10px] tracking-wider text-green uppercase">
            <Play className="size-3" aria-hidden="true" />
            {animatedLabel}
          </span>
        ) : null}
      </span>
    </button>
  );
}
