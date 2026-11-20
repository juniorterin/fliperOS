'use client';

import { Check, Copy, ExternalLink, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { LOCALES, LOCALE_NAME, LOCALE_SHORT, type Locale } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import { track } from '@/lib/analytics';
import { NETWORKS, SHARE_NETWORKS, SHARE_UPDATE, shareLength, shareText, shareUrl, type ShareNetwork } from '@/lib/share';
import { SocialIcon } from './SocialIcon';

const fill = (text: string, vars: Record<string, string | number>) =>
  text.replace(/\{(\w+)\}/g, (whole, key: string) => (key in vars ? String(vars[key]) : whole));

async function copyToClipboard(text: string, field: HTMLTextAreaElement | null): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Sem a API (http, permissão negada): seleciona o campo e usa o comando antigo.
    if (!field) return false;
    field.select();
    try {
      return document.execCommand('copy');
    } catch {
      return false;
    }
  }
}

// O modal do botão Compartilhar: a rede, o idioma e o texto pronto e do
// tamanho certo para ela (src/lib/share-texts.json), que dá para editar antes
// de postar.
export function ShareDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t, locale } = useI18n();
  const s = t.share;
  const ref = useRef<HTMLDialogElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const [network, setNetwork] = useState<ShareNetwork>('x');
  const [lang, setLang] = useState<Locale>(locale);
  // O texto editado à mão; null enquanto vale o texto pronto da rede e do idioma.
  const [draft, setDraft] = useState<string | null>(null);
  const [status, setStatus] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (open) {
      setLang(locale);
      setDraft(null);
      setStatus(null);
    }
  }, [open, locale]);

  const spec = NETWORKS[network];
  const text = draft ?? shareText(network, lang);
  const size = shareLength(network, text);
  const over = size > spec.max;

  const choose = (next: { network?: ShareNetwork; lang?: Locale }) => {
    if (next.network) setNetwork(next.network);
    if (next.lang) setLang(next.lang);
    setDraft(null);
    setStatus(null);
  };

  const copy = async () => {
    const ok = await copyToClipboard(text, field.current);
    setStatus(ok ? { kind: 'ok', text: s.copied } : { kind: 'error', text: s.copyFailed });
    if (ok) track('share_copy', { network, language: lang });
    return ok;
  };

  const share = async () => {
    // O endereço da rede abre antes da cópia, que é assíncrona: o navegador
    // só deixa abrir a janela dentro do clique.
    window.open(spec.open(text, shareUrl(lang)), '_blank', 'noopener,noreferrer');
    track('share_open', { network, language: lang });
    // Um texto longo no endereço da rede pode ser cortado: ele também vai
    // para a área de transferência, para colar se faltar um pedaço.
    if (spec.intent === 'text' && size <= 1500) {
      setStatus(null);
      return;
    }
    const ok = await copyToClipboard(text, field.current);
    setStatus(ok ? { kind: 'ok', text: fill(s.opened, { network: spec.name }) } : { kind: 'error', text: s.copyFailed });
  };

  const choiceClass = (active: boolean) =>
    `inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
      active ? 'border-purple bg-purple/15 text-fg' : 'border-line text-muted hover:border-purple/60 hover:text-fg'
    }`;

  const counterClass = over ? 'text-red' : 'text-comment';

  return (
    <dialog
      ref={ref}
      aria-labelledby="share-title"
      className="m-auto max-h-[94dvh] w-[min(720px,94vw)] max-w-none overflow-y-auto rounded-2xl border border-line bg-bg-deeper p-0 text-fg"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onClose={onClose}
    >
      <div className="grid gap-5 p-4 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 id="share-title" className="text-xl font-semibold">
              {s.title}
            </h2>
            <p className="mt-1 text-sm text-muted">{s.intro}</p>
          </div>
          <button type="button" onClick={onClose} aria-label={s.close} className="rounded-lg border border-line p-2 hover:border-pink">
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>

        <div role="group" aria-label={s.network} className="flex flex-wrap gap-2">
          {SHARE_NETWORKS.map((id) => (
            <button key={id} type="button" aria-pressed={id === network} onClick={() => choose({ network: id })} className={choiceClass(id === network)}>
              <SocialIcon network={id} className="size-4" />
              {NETWORKS[id].name}
            </button>
          ))}
        </div>

        <div role="group" aria-label={s.language} className="flex flex-wrap gap-2">
          {LOCALES.map((id) => (
            <button key={id} type="button" aria-pressed={id === lang} onClick={() => choose({ lang: id })} className={choiceClass(id === lang)}>
              <span className="font-mono text-xs text-comment">{LOCALE_SHORT[id]}</span>
              {LOCALE_NAME[id]}
            </button>
          ))}
        </div>

        <div className="grid gap-2">
          <label htmlFor="share-text" className="text-sm font-medium">
            {s.text}
          </label>
          <textarea
            id="share-text"
            ref={field}
            value={text}
            onChange={(e) => {
              setDraft(e.target.value);
              setStatus(null);
            }}
            rows={8}
            spellCheck={false}
            className="max-h-[42dvh] min-h-40 w-full resize-y [field-sizing:content] rounded-xl border border-line bg-bg-deep p-3 text-sm leading-relaxed text-fg"
          />
          <p className={`font-mono text-xs ${counterClass}`}>
            {fill(s.count, { n: size, max: spec.max })}
            {over ? ` · ${fill(s.tooLong, { network: spec.name })}` : null}
          </p>
        </div>

        <div className="grid gap-3">
          <p className="text-sm text-muted">{fill(s.hints[spec.intent], { network: spec.name })}</p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={share}
              className="inline-flex items-center gap-2 rounded-lg bg-purple px-4 py-2.5 text-sm font-medium text-bg-deeper transition hover:brightness-110"
            >
              <ExternalLink className="size-4" aria-hidden="true" />
              {fill(s.open, { network: spec.name })}
            </button>
            <button
              type="button"
              onClick={copy}
              className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2.5 text-sm font-medium transition-colors hover:border-purple"
            >
              {status?.kind === 'ok' ? <Check className="size-4 text-green" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
              {s.copy}
            </button>
            <span role="status" className={`text-sm ${status?.kind === 'error' ? 'text-red' : 'text-green'}`}>
              {status?.text}
            </span>
          </div>
        </div>

        <p className="font-mono text-xs text-comment">{fill(s.updated, { n: SHARE_UPDATE })}</p>
      </div>
    </dialog>
  );
}
