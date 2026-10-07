'use client';

import { Download, LayoutGrid } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';

// Monogramas no estilo dos ícones do menu do FliperOS (config/icons): sem logos de terceiros.
const MONOGRAM: Record<string, string> = {
  groovymame: 'GM',
  retroarch: 'RA',
  flycast: 'FC',
  pcsx2: 'P2',
  dolphin: 'DO',
  supermodel: 'SM',
  model2: 'M2',
  hypseus: 'HS',
  openbor: 'OB',
  'attract-mode': 'AM',
  'es-de': 'ES',
  pegasus: 'PG',
  fightcade: 'F2',
};

const ACCENTS = [
  'border-purple/60 text-purple',
  'border-pink/60 text-pink',
  'border-cyan/60 text-cyan',
  'border-green/60 text-green',
  'border-orange/60 text-orange',
];

function Monogram({ id, index, size = 'md' }: { id: string; index: number; size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'size-14 text-lg' : 'size-12 text-base';
  return (
    <span
      aria-hidden="true"
      className={`relative inline-flex shrink-0 items-center justify-center rounded-xl border-2 bg-bg font-mono font-bold ${box} ${
        ACCENTS[index % ACCENTS.length]
      }`}
    >
      {MONOGRAM[id] ?? id.slice(0, 2).toUpperCase()}
      <span className="absolute bottom-1 flex gap-0.5">
        <span className="size-1 rounded-full bg-pink" />
        <span className="size-1 rounded-full bg-green" />
        <span className="size-1 rounded-full bg-cyan" />
      </span>
    </span>
  );
}

export function Emulators() {
  const { t } = useI18n();
  const e = t.emulators;
  return (
    <section id="emulators" aria-labelledby="emulators-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="emulators" kicker={e.kicker} title={e.title} intro={e.intro} />

        <h3 className="mt-14 flex items-center gap-3 font-mono text-sm tracking-widest text-comment uppercase">
          {e.emulatorsTitle}
          <span aria-hidden="true" className="h-px flex-1 bg-line" />
        </h3>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {e.items.map((item, i) => (
            <Reveal as="li" key={item.id} delay={(i % 3) * 60}>
              <article className="card flex h-full items-start gap-4 rounded-xl p-4">
                <Monogram id={item.id} index={i} />
                <div className="min-w-0">
                  <h4 className="font-semibold text-fg">{item.name}</h4>
                  <p className="mt-0.5 text-sm text-cyan">{item.systems}</p>
                  <p className="mt-1 font-mono text-xs text-muted">{item.note}</p>
                </div>
              </article>
            </Reveal>
          ))}
        </ul>

        <div className="mt-16 rounded-2xl border border-line bg-gradient-to-br from-bg to-bg-deeper p-6 sm:p-8">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <h3 className="flex items-center gap-2.5 text-2xl font-semibold text-fg">
              <LayoutGrid className="size-6 text-pink" aria-hidden="true" />
              {e.frontendsTitle}
            </h3>
            <p className="font-mono text-sm text-muted">{e.frontendsIntro}</p>
          </div>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {e.frontends.map((item, i) => (
              <Reveal as="li" key={item.id} delay={i * 60}>
                <article className="card flex h-full flex-col gap-4 rounded-xl p-5">
                  <Monogram id={item.id} index={i + 1} size="lg" />
                  <div>
                    <h4 className="font-semibold text-fg">{item.name}</h4>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{item.text}</p>
                  </div>
                </article>
              </Reveal>
            ))}
          </ul>
        </div>

        <Reveal className="mt-8 rounded-2xl border border-dashed border-line p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:gap-8">
            <div className="lg:max-w-sm">
              <h3 className="flex items-center gap-2 font-semibold text-fg">
                <Download className="size-4 text-orange" aria-hidden="true" />
                {e.extrasTitle}
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{e.extrasText}</p>
            </div>
            <ul className="flex flex-1 flex-wrap gap-3">
              {e.extras.map((item) => (
                <li key={item.id} className="flex items-center gap-3 rounded-lg border border-line bg-bg-deeper/60 px-3.5 py-2.5">
                  <span className="rounded border border-orange/50 px-1.5 py-0.5 font-mono text-[10px] tracking-wider text-orange uppercase">
                    {e.extrasBadge}
                  </span>
                  <span>
                    <span className="block text-sm font-medium text-fg">{item.name}</span>
                    <span className="block text-xs text-muted">{item.text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
