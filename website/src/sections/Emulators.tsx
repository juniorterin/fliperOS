'use client';

import Image from 'next/image';
import { ArrowUpRight, Download, LayoutGrid, Network } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

// A cor de cada nível de net play na tabela.
const LEVEL: Record<string, string> = {
  frontend: 'border-green/60 bg-green/10 text-green',
  hand: 'border-cyan/60 text-cyan',
  partial: 'border-orange/60 text-orange',
  no: 'border-line text-comment',
};

// Ícones oficiais de cada projeto (public/icons, origem no README de lá).
const ICON: Record<string, string> = {
  groovymame: '/icons/groovymame.png',
  retroarch: '/icons/retroarch.svg',
  flycast: '/icons/flycast.png',
  pcsx2: '/icons/pcsx2.png',
  pcsx2x6: '/icons/pcsx2x6.png',
  dolphin: '/icons/dolphin.svg',
  model2: '/icons/model2.png',
  openbor: '/icons/openbor.png',
  'attract-mode': '/icons/attract-mode.png',
  'es-de': '/icons/es-de.svg',
  pegasus: '/icons/pegasus.png',
  fightcade: '/icons/fightcade.png',
  fliperos: '/fliperos-logo.png',
};

// Monogramas no estilo dos ícones do menu do FliperOS, para quem não tem ícone próprio.
const MONOGRAM: Record<string, string> = {
  groovymame: 'GM',
  retroarch: 'RA',
  flycast: 'FC',
  pcsx2: 'P2',
  duckstation: 'DS',
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
  const icon = ICON[id];
  if (icon) {
    const px = size === 'lg' ? 56 : 48;
    return (
      <Image
        src={icon}
        alt=""
        aria-hidden="true"
        width={px}
        height={px}
        unoptimized
        className={`shrink-0 object-contain ${box}`}
      />
    );
  }
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

        <h3 className="mt-14 flex items-center gap-3 font-mono text-sm tracking-widest text-comment uppercase">
          {e.gamesTitle}
          <span aria-hidden="true" className="h-px flex-1 bg-line" />
        </h3>
        <ul className="mt-6 grid gap-4">
          {e.games.map((game) => (
            <Reveal as="li" key={game.id}>
              <article className="card flex flex-col gap-5 rounded-2xl p-5 sm:flex-row sm:items-center sm:p-6">
                {/* O logotipo do projeto (public/icons/README.md diz de onde veio). */}
                <a href={game.url} target="_blank" rel="noopener noreferrer" className="shrink-0 self-center">
                  <Image
                    src={`/icons/${game.id}.png`}
                    alt={game.logoAlt}
                    width={240}
                    height={97}
                    unoptimized
                    className="h-auto w-60 rounded-lg"
                  />
                  <span className="sr-only">{t.a11y.external}</span>
                </a>
                <div className="min-w-0">
                  <h4 className="text-lg font-semibold text-fg">{game.name}</h4>
                  <p className="mt-0.5 text-sm text-cyan">{game.by}</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{game.text}</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <a
                      href={game.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg border border-orange/60 bg-orange/10 px-4 py-2 text-sm font-medium text-fg transition hover:border-orange hover:bg-orange/20"
                    >
                      {game.cta}
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                      <span className="sr-only">{t.a11y.external}</span>
                    </a>
                    <a
                      href={game.site}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-medium text-fg transition hover:border-purple/60 hover:text-purple"
                    >
                      {game.siteCta}
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                      <span className="sr-only">{t.a11y.external}</span>
                    </a>
                  </div>
                </div>
              </article>
            </Reveal>
          ))}
        </ul>

        <Reveal className="mt-16 rounded-2xl border border-line p-6 sm:p-8">
          <h3 className="flex items-center gap-2.5 text-2xl font-semibold text-fg">
            <Network className="size-6 text-green" aria-hidden="true" />
            {e.netplayTitle}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">{e.netplayIntro}</p>
          <table className="mt-6 w-full text-left text-sm">
            <thead className="hidden font-mono text-xs tracking-wider text-comment uppercase sm:table-header-group">
              <tr className="border-b border-line">
                <th scope="col" className="py-2 pr-4 font-normal">{e.netplayHead.name}</th>
                <th scope="col" className="py-2 pr-4 font-normal">{e.netplayHead.systems}</th>
                <th scope="col" className="py-2 font-normal">{e.netplayHead.status}</th>
              </tr>
            </thead>
            <tbody>
              {e.netplay.map((row) => (
                <tr key={row.id} className="flex flex-col gap-1 border-b border-line/60 py-3 sm:table-row sm:py-0">
                  <th scope="row" className="font-semibold text-fg sm:py-2.5 sm:pr-4">{row.name}</th>
                  <td className="text-cyan sm:py-2.5 sm:pr-4">{row.systems}</td>
                  <td className="sm:py-2.5">
                    <span
                      className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[10px] tracking-wider uppercase ${LEVEL[row.level]}`}
                    >
                      {e.netplayLevels[row.level as keyof typeof e.netplayLevels]}
                    </span>
                    {row.note && <span className="ml-2 text-xs text-muted">{row.note}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <a
            href={`${LINKS.docs}/Linked-cabinets`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-green/60 bg-green/10 px-4 py-2.5 text-sm font-medium text-fg transition hover:border-green hover:bg-green/20"
          >
            {e.netplayCta}
            <ArrowUpRight className="size-4" aria-hidden="true" />
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </Reveal>

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
