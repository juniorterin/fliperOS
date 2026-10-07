'use client';

import { useReportWebVitals } from 'next/web-vitals';
import { useEffect } from 'react';
import { linkEvent, track } from '@/lib/analytics';

function sectionOf(el: Element): string {
  return el.closest('section[id], header, footer')?.getAttribute('id') ?? el.closest('header, footer')?.tagName.toLowerCase() ?? 'page';
}

function labelOf(el: HTMLElement): string {
  return (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100);
}

// Eventos além da medição otimizada do GA4: cliques com contexto, seções vistas,
// profundidade de rolagem, cópia de texto, erros de JavaScript e Web Vitals.
export function AnalyticsEvents() {
  useReportWebVitals((metric) => {
    track('web_vitals', {
      metric_name: metric.name,
      metric_value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      metric_rating: metric.rating,
      metric_id: metric.id,
      non_interaction: true,
    });
  });

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const el = (e.target as Element | null)?.closest<HTMLElement>('a, button, summary, [role="button"]');
      if (!el) return;
      const custom = el.dataset.ga;
      const params: Record<string, unknown> = {
        element: el.tagName.toLowerCase(),
        label: labelOf(el),
        section: sectionOf(el),
      };
      if (el instanceof HTMLAnchorElement) {
        const href = el.getAttribute('href') ?? '';
        params.link_url = el.href;
        params.outbound = el.host !== window.location.host;
        track(custom ?? linkEvent(href), params);
      } else {
        track(custom ?? 'click_button', params);
      }
    };

    const onCopy = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim() ?? '';
      if (!text) return;
      const node = selection?.anchorNode;
      const el = node instanceof Element ? node : node?.parentElement;
      track('copy_text', { section: el ? sectionOf(el) : 'page', text: text.slice(0, 100), length: text.length });
    };

    const onError = (e: ErrorEvent) => {
      track('exception', { description: `${e.message} @ ${e.filename}:${e.lineno}`.slice(0, 150), fatal: false });
    };
    const onRejection = (e: PromiseRejectionEvent) => {
      track('exception', { description: String(e.reason).slice(0, 150), fatal: false });
    };

    const seen = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.id;
          if (entry.isIntersecting && !seen.has(id)) {
            seen.add(id);
            track('section_view', { section: id, non_interaction: true });
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.4 },
    );
    document.querySelectorAll('section[id]').forEach((s) => observer.observe(s));

    const marks = [25, 50, 75, 100];
    const reached = new Set<number>();
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const pct = max > 0 ? (window.scrollY / max) * 100 : 100;
      for (const m of marks) {
        if (pct >= m - 1 && !reached.has(m)) {
          reached.add(m);
          track('scroll_depth', { percent: m, non_interaction: true });
        }
      }
    };

    document.addEventListener('click', onClick, { capture: true });
    document.addEventListener('copy', onCopy);
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      document.removeEventListener('click', onClick, { capture: true });
      document.removeEventListener('copy', onCopy);
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
      window.removeEventListener('scroll', onScroll);
      observer.disconnect();
    };
  }, []);

  return null;
}
