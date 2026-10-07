'use client';

import { Briefcase, Check, Copy, ExternalLink, Heart, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { CONTACT_EMAIL, DONATE_URL, PIX_KEY } from '@/lib/site';

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Sem a Clipboard API (http, navegador antigo): a seleção de um textarea.
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    return ok;
  }
}

export function Support() {
  const { t, locale } = useI18n();
  const s = t.support;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [copied, setCopied] = useState(false);
  // O Pix só existe no Brasil: em inglês a doação é só pelo Stripe.
  const showPix = locale.startsWith('pt');

  const copyPix = async () => {
    if (await copyText(PIX_KEY)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <section id="support" aria-labelledby="support-title" className="relative py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-pink/50 to-transparent" />
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="support" kicker={s.kicker} title={s.title} intro={s.intro} align="center" />

        <div className="mt-14 grid gap-5 md:grid-cols-2">
          <Reveal className="h-full">
            <div className="card flex h-full flex-col rounded-2xl p-6 sm:p-8">
              <span className="inline-flex size-12 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10 text-cyan">
                <Briefcase className="size-6" aria-hidden="true" />
              </span>
              <h3 className="mt-5 text-xl font-semibold text-fg">{s.consultingTitle}</h3>
              <p className="mt-3 leading-relaxed text-pretty text-muted">{s.consultingText}</p>
              <p className="mt-auto pt-6 text-sm text-comment">{s.contactLabel}</p>
              <p className="mt-2 font-mono text-lg break-all text-fg select-all sm:text-xl" aria-label={s.emailAria}>
                {CONTACT_EMAIL.user} <strong className="font-bold text-pink">@</strong> {CONTACT_EMAIL.domain}{' '}
                <strong className="font-bold text-green">.</strong> {CONTACT_EMAIL.tld}
              </p>
            </div>
          </Reveal>

          <Reveal className="h-full" delay={80}>
            <div className="card flex h-full flex-col rounded-2xl p-6 sm:p-8">
              <span className="inline-flex size-12 items-center justify-center rounded-xl border border-pink/40 bg-pink/10 text-pink">
                <Heart className="size-6" aria-hidden="true" />
              </span>
              <h3 className="mt-5 text-xl font-semibold text-fg">{s.donateTitle}</h3>
              <p className="mt-3 leading-relaxed text-pretty text-muted">{s.donateText}</p>

              <div className="mt-auto flex flex-col gap-3 pt-6">
                {showPix ? (
                  <button
                    type="button"
                    onClick={copyPix}
                    data-ga="pix_copy"
                    title={s.pixCopyTitle}
                    className="group flex items-center gap-3 rounded-xl border border-green/40 bg-bg-deeper/70 px-4 py-3 text-left transition hover:border-green"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block font-mono text-xs tracking-wider text-green uppercase">{s.pixLabel}</span>
                      <span className="block truncate font-mono text-sm text-fg">{PIX_KEY}</span>
                    </span>
                    <span aria-live="polite" className="flex shrink-0 items-center gap-1.5 text-sm text-green">
                      {copied ? <Check className="size-4" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
                      {copied ? s.pixCopied : s.pixCopy}
                    </span>
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => dialogRef.current?.showModal()}
                  data-ga="donate_open"
                  className="inline-flex items-center justify-center gap-2.5 rounded-xl bg-pink px-6 py-3.5 font-semibold text-bg-deeper shadow-[0_10px_40px_-10px] shadow-pink transition hover:-translate-y-0.5 hover:bg-[#ff94d2]"
                >
                  <Heart className="size-5" aria-hidden="true" />
                  {s.donateCta}
                </button>
              </div>
            </div>
          </Reveal>
        </div>
      </div>

      <dialog
        ref={dialogRef}
        aria-labelledby="donate-modal-title"
        className="m-auto w-[min(480px,92vw)] max-w-none rounded-2xl border border-line bg-bg-deeper p-0 text-fg backdrop:bg-black/70"
        onClick={(e) => e.target === e.currentTarget && dialogRef.current?.close()}
      >
        <div className="flex items-center gap-3 border-b border-line px-5 py-4">
          <Heart className="size-5 text-pink" aria-hidden="true" />
          <h3 id="donate-modal-title" className="flex-1 font-semibold">
            {s.modalTitle}
          </h3>
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            aria-label={s.modalClose}
            className="rounded-lg border border-line p-2 hover:border-pink"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
        <div className="px-5 py-6">
          <p className="leading-relaxed text-pretty text-muted">{s.modalText}</p>
          <a
            href={DONATE_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-ga="donate_stripe_click"
            onClick={() => dialogRef.current?.close()}
            className="mt-6 flex items-center justify-center gap-2.5 rounded-xl bg-purple px-6 py-3.5 font-semibold text-bg-deeper transition hover:bg-[#c9a6fb]"
            autoFocus
          >
            {s.modalContinue}
            <ExternalLink className="size-4" aria-hidden="true" />
          </a>
        </div>
      </dialog>
    </section>
  );
}
