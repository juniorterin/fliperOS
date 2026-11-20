import { Send } from 'lucide-react';
import type { ShareNetwork } from '@/lib/share';

// Marcas das redes do botão Compartilhar, em traço simples (o Lucide 1.x não
// traz mais ícones de marcas).
export function SocialIcon({ network, className = 'size-5' }: { network: ShareNetwork; className?: string }) {
  if (network === 'telegram') return <Send className={className} aria-hidden="true" />;
  const common = { viewBox: '0 0 24 24', 'aria-hidden': true, focusable: false, className } as const;
  if (network === 'x') {
    return (
      <svg {...common} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
        <path d="M4.5 4.5 19.5 19.5M19.5 4.5l-15 15" />
      </svg>
    );
  }
  if (network === 'instagram') {
    return (
      <svg {...common} fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.2" cy="6.8" r="0.6" fill="currentColor" />
      </svg>
    );
  }
  if (network === 'facebook') {
    return (
      <svg {...common} fill="currentColor">
        <path d="M13.5 21v-8h2.7l.5-3.3h-3.2V7.6c0-.9.4-1.7 1.8-1.7h1.5V3.1C16.5 3 15.6 3 14.7 3c-2.6 0-4.4 1.6-4.4 4.5v2.2H7.5V13h2.8v8Z" />
      </svg>
    );
  }
  return (
    <svg {...common} fill="currentColor">
      <rect x="3.5" y="9" width="3.6" height="11.5" />
      <circle cx="5.3" cy="5.3" r="2.1" />
      <path d="M9.8 9h3.4v1.6c.6-1.1 1.9-1.9 3.6-1.9 3.2 0 3.7 2.1 3.7 4.8v6h-3.6v-5.3c0-1.3 0-2.9-1.8-2.9-1.8 0-2.1 1.4-2.1 2.8v5.4H9.8Z" />
    </svg>
  );
}
