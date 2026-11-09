'use client';

import Image from 'next/image';
import { ArrowUpRight, Crosshair, Gamepad2, Lightbulb, MemoryStick, MonitorDot, Zap, type LucideIcon } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

const ITEM_STYLE: Record<string, { icon: LucideIcon; color: string }> = {
  display: { icon: MonitorDot, color: 'text-pink border-pink/40 bg-pink/10' },
  panel: { icon: Gamepad2, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  gun: { icon: Crosshair, color: 'text-orange border-orange/40 bg-orange/10' },
  outputs: { icon: Zap, color: 'text-yellow border-yellow/40 bg-yellow/10' },
  lights: { icon: Lightbulb, color: 'text-green border-green/40 bg-green/10' },
  cart: { icon: MemoryStick, color: 'text-purple border-purple/40 bg-purple/10' },
};

// Os projetos de cada cartao, pelo nome que aparece nele.
const PROJECT_URL: Record<string, string> = {
  ZeDMD: 'https://github.com/PPUC/ZeDMD',
  libdmdutil: 'https://github.com/vpinball/libdmdutil',
  'GP2040-CE': 'https://github.com/OpenStickCommunity/GP2040-CE',
  'DaemonBite Arcade Encoder': 'https://github.com/MickGyver/DaemonBite-Arcade-Encoder',
  'Arduino Joystick Library': 'https://github.com/MHeironimus/ArduinoJoystickLibrary',
  'Arcade Spinner': 'https://github.com/jmtw000/Arcade-Spinner',
  OpenFIRE: 'https://github.com/TeamOpenFIRE/OpenFIRE-Firmware',
  'Hook Of The Reaper': 'https://hotr.6bolt.com/',
  QMamehook: 'https://github.com/SeongGino/QMamehook',
  LEDSpicer: 'https://github.com/meduzapat/LEDSpicer',
  'Open Source Cartridge Reader': 'https://github.com/sanni/cartreader',
};

// Os dois aparelhos com foto: a GunCon 2 (Wikimedia Commons, CC BY-SA 3.0) e o
// OSCR HW5 (wiki do projeto, CC0). O crédito de cada foto vai na legenda.
const PHOTO_CARDS = [
  { id: 'guncon', src: '/art/guncon-2.webp', width: 800, height: 648, docs: 'Controls#light-gun-guncon-2', shop: undefined },
  { id: 'oscr', src: '/art/oscr-hw5.webp', width: 640, height: 565, docs: 'DIY-hardware#cartridge-reader-open-source-cartridge-reader', shop: LINKS.oscr },
] as const;

export function OpenHardware() {
  const { t } = useI18n();
  const o = t.openHardware;
  return (
    <section id="open-hardware" aria-labelledby="open-hardware-title" className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-green/40 to-transparent" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="open-hardware" kicker={o.kicker} title={o.title} intro={o.intro} />

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {o.items.map((item, i) => {
            const style = ITEM_STYLE[item.id] ?? ITEM_STYLE.panel;
            const Icon = style.icon;
            return (
              <Reveal as="li" key={item.id} delay={i * 60}>
                <article className="card flex h-full flex-col rounded-2xl p-5">
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl border ${style.color}`}>
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <div>
                      <h3 className="font-semibold text-fg">{item.title}</h3>
                      <p className="font-mono text-xs text-comment">{item.boards}</p>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-muted">{item.text}</p>
                  <ul className="mt-auto flex flex-wrap gap-2 pt-4">
                    {item.projects.map((name) => (
                      <li key={name}>
                        <a
                          href={PROJECT_URL[name] ?? `${LINKS.docs}/DIY-hardware`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded-md border border-line bg-bg-deeper/70 px-2.5 py-1 font-mono text-xs text-fg transition hover:border-comment"
                        >
                          {name}
                          <ArrowUpRight className="size-3 text-comment" aria-hidden="true" />
                          <span className="sr-only">{t.a11y.external}</span>
                        </a>
                      </li>
                    ))}
                  </ul>
                </article>
              </Reveal>
            );
          })}
        </ul>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {PHOTO_CARDS.map((card, i) => {
            const c = o[card.id];
            const links = [
              ...(card.shop ? [{ href: card.shop, label: o.oscr.cta }] : []),
              { href: `${LINKS.docs}/${card.docs}`, label: c.docs },
            ];
            return (
              <Reveal key={card.id} delay={i * 80}>
                <article className="card flex h-full flex-col gap-5 rounded-2xl p-5 sm:flex-row sm:p-6 lg:flex-col">
                  <figure className="shrink-0 sm:w-56 lg:w-full">
                    <Image
                      src={card.src}
                      alt={c.alt}
                      width={card.width}
                      height={card.height}
                      unoptimized
                      className="aspect-[4/3] h-auto w-full rounded-xl object-cover"
                    />
                    <figcaption className="mt-2 text-[11px] leading-snug text-comment">{c.credit}</figcaption>
                  </figure>
                  <div>
                    <h3 className="font-semibold text-fg">{c.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted">{c.text}</p>
                    <p className="mt-2 text-sm leading-relaxed text-muted">{c.note}</p>
                    <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
                      {links.map((link) => (
                        <a
                          key={link.href}
                          href={link.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm font-medium text-cyan transition-colors hover:text-fg"
                        >
                          {link.label}
                          <ArrowUpRight className="size-4" aria-hidden="true" />
                          <span className="sr-only">{t.a11y.external}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>

        <Reveal className="mt-10 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <p className="max-w-2xl text-xs leading-relaxed text-comment">{o.disclaimer}</p>
          <a
            href={`${LINKS.docs}/DIY-hardware`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-green/60 bg-green/10 px-4 py-2.5 text-sm font-medium text-fg transition hover:border-green hover:bg-green/20 hover:shadow-[0_0_20px_-6px] hover:shadow-green"
          >
            {o.cta}
            <ArrowUpRight className="size-4" aria-hidden="true" />
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </Reveal>
      </div>
    </section>
  );
}
