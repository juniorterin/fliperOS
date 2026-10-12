'use client';

import { ArrowUpRight, Crosshair, Gamepad2, Lightbulb, MonitorDot, Zap, type LucideIcon } from 'lucide-react';
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
};

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
