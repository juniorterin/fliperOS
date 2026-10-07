type Gtag = (command: 'event' | 'consent', name: string, params?: Record<string, unknown>) => void;

export const CONSENT_KEY = 'fliperos-cookies';

function gtag(): Gtag | null {
  if (typeof window === 'undefined') return null;
  const fn = (window as unknown as { gtag?: Gtag }).gtag;
  return typeof fn === 'function' ? fn : null;
}

// Sem o gtag (dev, bloqueador de anúncios) os eventos são descartados em silêncio.
export function track(name: string, params: Record<string, unknown> = {}) {
  gtag()?.('event', name, params);
}

export function setConsent(granted: boolean) {
  try {
    window.localStorage.setItem(CONSENT_KEY, granted ? 'granted' : 'denied');
  } catch {
    // localStorage bloqueado: a escolha vale só nesta visita.
  }
  gtag()?.('consent', 'update', { analytics_storage: granted ? 'granted' : 'denied' });
}

// Nome do evento para um link conhecido do site; o resto vira click_link.
export function linkEvent(href: string): string {
  if (/\/releases(\/|$)/.test(href) || /\.iso(\?|$)/.test(href)) return 'download_click';
  if (/\/wiki(\/|$)/.test(href)) return 'docs_click';
  if (/\/issues(\/|$)/.test(href)) return 'issues_click';
  if (/instagram\.com/.test(href)) return 'instagram_click';
  if (/github\.com/.test(href)) return 'github_click';
  if (href.startsWith('#') || /^\/(en|pt)(#|$)/.test(href)) return 'nav_click';
  return 'click_link';
}
