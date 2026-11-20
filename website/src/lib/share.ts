import { localePath, type Locale } from '@/i18n';
import data from './share-texts.json';
import { FLIPEROS_VERSION, SITE_URL } from './site';

// As redes do botão Compartilhar, na ordem do modal. Os textos de cada uma
// (nos dois idiomas) ficam em share-texts.json, a lista de linhas por rede.
export const SHARE_NETWORKS = ['x', 'instagram', 'facebook', 'linkedin', 'telegram'] as const;
export type ShareNetwork = (typeof SHARE_NETWORKS)[number];

type NetworkSpec = {
  name: string;
  // O limite de caracteres da rede: os textos ocupam de 95% dele até ele
  // inteiro (o modal mostra o contador, e scripts/check-share.mjs confere).
  // A checagem lê esta tabela: mudou aqui, vale lá.
  max: number;
  // Como a rede recebe o texto: "text" abre a caixa de post já com ele,
  // "url" só aceita o link (o texto vai para a área de transferência e o
  // usuário cola), "none" não tem endereço de compartilhar (Instagram).
  intent: 'text' | 'url' | 'none';
  open: (text: string, url: string) => string;
};

export const NETWORKS: Record<ShareNetwork, NetworkSpec> = {
  // O X conta qualquer link como 23 caracteres.
  x: {
    name: 'X',
    max: 280,
    intent: 'text',
    open: (text) => `https://x.com/intent/post?text=${encodeURIComponent(text)}`,
  },
  instagram: {
    name: 'Instagram',
    max: 2200,
    intent: 'none',
    open: () => 'https://www.instagram.com/',
  },
  facebook: {
    name: 'Facebook',
    max: 3000,
    intent: 'url',
    open: (_text, url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
  },
  linkedin: {
    name: 'LinkedIn',
    max: 3000,
    intent: 'url',
    open: (_text, url) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
  },
  telegram: {
    name: 'Telegram',
    max: 4096,
    intent: 'text',
    // O Telegram junta o link ao texto: o {url} do texto sai daqui.
    open: (text, url) =>
      `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text.replace(url, '').trim())}`,
  },
};

// O número do último update que os textos já contam (share-texts.json).
export const SHARE_UPDATE: number = data.update;

const TEXTS = data.texts as Record<Locale, Record<ShareNetwork, string[]>>;

// Quanto o texto pesa na rede: o X conta cada link como 23 caracteres. Um
// emoji conta como 2 (length em UTF-16), a conta mais cautelosa das redes.
export function shareLength(network: ShareNetwork, text: string): number {
  const counted = network === 'x' ? text.replace(/https?:\/\/\S+/g, 'x'.repeat(23)) : text;
  return counted.length;
}

// O endereço que vai no texto: a home do site no idioma do texto.
export function shareUrl(locale: Locale): string {
  return `${SITE_URL}${localePath(locale)}`;
}

// O texto pronto da rede no idioma, com o endereço e a versão no lugar.
export function shareText(network: ShareNetwork, locale: Locale): string {
  return TEXTS[locale][network]
    .join('\n')
    .replaceAll('{url}', shareUrl(locale))
    .replaceAll('{version}', FLIPEROS_VERSION);
}
