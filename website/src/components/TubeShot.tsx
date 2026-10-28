import Image from 'next/image';
import type { Media } from '@/lib/media';

// Uma tela na moldura do tubo, sem clique: para os cartões que já são links.
export function TubeShot({ media, sizes, className = '' }: { media: Media; sizes: string; className?: string }) {
  return (
    <span className={`crt-bezel block rounded-2xl p-2 ${className}`}>
      <span className="relative block aspect-[4/3] w-full overflow-hidden rounded-lg bg-bg-deeper">
        <Image
          src={media.src}
          alt={media.alt}
          fill
          sizes={sizes}
          unoptimized
          className={`object-contain ${media.pixelated ? '[image-rendering:pixelated]' : ''}`}
        />
      </span>
    </span>
  );
}
