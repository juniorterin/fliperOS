'use client';

import { Gamepad2, Keyboard, SlidersHorizontal } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';

export function Setup() {
  const { t } = useI18n();
  const s = t.setup;
  return (
    <section id="setup" aria-labelledby="setup-title" className="relative py-24 sm:py-32">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
        <div>
          <SectionHeading id="setup" kicker={s.kicker} title={s.title} intro={s.intro} />
          <Reveal className="mt-8 flex flex-wrap gap-3 text-muted" delay={100}>
            <span className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2">
              <Gamepad2 className="size-4 text-pink" aria-hidden="true" />
              <Keyboard className="size-4 text-cyan" aria-hidden="true" />
              <SlidersHorizontal className="size-4 text-orange" aria-hidden="true" />
              <span className="font-mono text-xs">{s.hint}</span>
            </span>
          </Reveal>
        </div>

        <Reveal delay={120}>
          <div className="overflow-hidden rounded-2xl border border-line bg-bg shadow-[0_30px_80px_-30px] shadow-black">
            <div className="flex items-center gap-2 border-b border-line bg-bg-deeper px-4 py-3">
              <span aria-hidden="true" className="size-3 rounded-full bg-red/80" />
              <span aria-hidden="true" className="size-3 rounded-full bg-yellow/80" />
              <span aria-hidden="true" className="size-3 rounded-full bg-green/80" />
              <span className="ml-3 font-mono text-xs text-comment">{s.terminalTitle}</span>
            </div>
            <div className="relative p-4 font-mono text-sm sm:p-6">
              <p className="text-pink">{s.menuTitle}</p>
              <ul className="mt-4 space-y-1">
                {s.menu.map((item, i) => (
                  <li
                    key={item.id}
                    className={`flex flex-col gap-0.5 rounded-md px-3 py-2 sm:flex-row sm:items-baseline sm:gap-4 ${
                      i === 0 ? 'bg-line/70 text-fg' : 'text-muted'
                    }`}
                  >
                    <span className={`shrink-0 sm:w-52 ${i === 0 ? 'text-purple' : ''}`}>
                      <span aria-hidden="true" className={i === 0 ? 'text-pink' : 'text-transparent'}>
                        {'> '}
                      </span>
                      {item.label}
                    </span>
                    <span className="pl-4 text-xs text-comment sm:pl-0">{item.text}</span>
                  </li>
                ))}
              </ul>
              <p aria-hidden="true" className="cursor-blink mt-5 text-xs text-comment">
                fliperos@fliperos:~$
              </p>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
