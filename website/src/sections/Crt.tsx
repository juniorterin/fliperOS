'use client';

import { Cpu, Gamepad2, Monitor, MonitorCog, type LucideIcon } from 'lucide-react';
import { Fragment } from 'react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';

const STEP_STYLE: Record<string, { icon: LucideIcon; color: string }> = {
  game: { icon: Gamepad2, color: 'text-pink border-pink/40 bg-pink/10' },
  switchres: { icon: MonitorCog, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  gpu: { icon: Cpu, color: 'text-orange border-orange/40 bg-orange/10' },
  crt: { icon: Monitor, color: 'text-green border-green/40 bg-green/10' },
};

export function Crt() {
  const { t } = useI18n();
  const c = t.crt;
  return (
    <section id="crt" aria-labelledby="crt-title" className="relative overflow-hidden bg-bg-deeper/40 py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan/40 to-transparent" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -bottom-40 -left-40 h-[500px] w-[700px]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="crt" kicker={c.kicker} title={c.title} intro={c.intro} />

        <Reveal className="mt-14">
          <figure className="crt-bezel rounded-3xl p-5 sm:p-8">
            <figcaption className="font-mono text-xs tracking-widest text-comment uppercase">{c.pipelineLabel}</figcaption>
            <ol className="mt-6 flex flex-col items-stretch gap-0 lg:flex-row lg:items-center">
              {c.steps.map((step, i) => {
                const style = STEP_STYLE[step.id] ?? STEP_STYLE.game;
                const Icon = style.icon;
                return (
                  <Fragment key={step.id}>
                    {i > 0 ? (
                      <li aria-hidden="true" className="flex justify-center lg:flex-1">
                        <span className="signal block h-8 w-0.5 bg-line lg:h-0.5 lg:w-full" />
                      </li>
                    ) : null}
                    <li className="flex items-start gap-4 rounded-2xl border border-line bg-bg/80 p-4 lg:w-56 lg:flex-col lg:items-center lg:text-center">
                      <span className={`inline-flex size-12 shrink-0 items-center justify-center rounded-xl border ${style.color}`}>
                        <Icon className="size-6" aria-hidden="true" />
                      </span>
                      <span>
                        <span className="block font-mono font-semibold text-fg">{step.label}</span>
                        <span className="mt-1 block text-sm leading-snug text-muted">{step.text}</span>
                      </span>
                    </li>
                  </Fragment>
                );
              })}
            </ol>
            <div aria-hidden="true" className="mt-6 overflow-x-auto rounded-lg border border-line/70 bg-bg-deeper/80 px-4 py-3 font-mono text-xs text-muted">
              <span className="text-green">switchres</span> <span className="text-comment">{'→'}</span>{' '}
              <span className="text-cyan">SR-1_384x224@59.64</span>
            </div>
          </figure>
        </Reveal>

        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {c.points.map((p, i) => (
            <Reveal as="li" key={p.id} delay={i * 60}>
              <div className="h-full border-l-2 border-purple/60 pl-4">
                <h3 className="font-semibold text-fg">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{p.text}</p>
              </div>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
