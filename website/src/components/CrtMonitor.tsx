import Image from 'next/image';
import { ImagePlus } from 'lucide-react';

type Props = {
  src: string | null;
  alt: string;
  placeholderTitle: string;
  placeholderHint: string;
  expectedPath: string;
  priority?: boolean;
};

// Moldura de monitor arcade. Sem screenshot real, mostra onde o arquivo deve ficar.
export function CrtMonitor({ src, alt, placeholderTitle, placeholderHint, expectedPath, priority }: Props) {
  return (
    <div className="crt-bezel rounded-[28px] p-4 sm:p-5">
      <div className="crt-screen aspect-[4/3] w-full">
        {src ? (
          <Image
            src={src}
            alt={alt}
            fill
            priority={priority}
            sizes="(min-width: 1024px) 560px, 92vw"
            className="object-cover"
          />
        ) : (
          <div className="flicker absolute inset-0 z-[1] flex flex-col items-center justify-center gap-4 p-6 text-center">
            <ImagePlus className="phosphor size-10 text-purple" aria-hidden="true" />
            <p className="phosphor font-mono text-sm font-semibold tracking-wider text-green uppercase sm:text-base">
              {placeholderTitle}
            </p>
            <p className="max-w-xs font-mono text-xs leading-relaxed text-muted sm:text-sm">
              {placeholderHint}
              <br />
              <code className="mt-1 inline-block rounded bg-bg-deeper/80 px-2 py-1 text-cyan">{expectedPath}</code>
            </p>
          </div>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between px-2" aria-hidden="true">
        <span className="font-mono text-[10px] tracking-[0.3em] text-comment uppercase">15 kHz</span>
        <span className="flex gap-1.5">
          <span className="size-2 rounded-full bg-pink/80" />
          <span className="size-2 rounded-full bg-green/80 shadow-[0_0_8px] shadow-green" />
          <span className="size-2 rounded-full bg-cyan/80" />
        </span>
      </div>
    </div>
  );
}
