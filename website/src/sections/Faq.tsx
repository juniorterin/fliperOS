'use client';

import { ChevronDown } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';

// As perguntas do FAQPage do JSON-LD (meta.faq), visiveis na pagina: o Google
// so aceita o dado estruturado com o mesmo texto na tela.
export function Faq() {
  const { t } = useI18n();
  return (
    <section id="faq" aria-labelledby="faq-title" className="relative py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-purple/40 to-transparent" />
      <div className="relative mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="faq" kicker={t.faqSection.kicker} title={t.faqSection.title} />
        <div className="mt-10 grid gap-3">
          {t.meta.faq.map((f, i) => (
            <Reveal key={f.q} delay={i * 40}>
              <details className="card group rounded-2xl p-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-fg">
                  {f.q}
                  <ChevronDown className="size-5 flex-none text-comment transition group-open:rotate-180" aria-hidden="true" />
                </summary>
                <p className="mt-3 leading-relaxed text-muted">{f.a}</p>
              </details>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
