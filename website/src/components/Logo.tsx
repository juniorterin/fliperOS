// Tubo de CRT com três botões, no estilo dos ícones do menu do FliperOS (config/icons).
export function LogoMark({ className = 'size-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" className={className}>
      <rect x="3" y="3" width="58" height="58" rx="13" fill="#282a36" stroke="#bd93f9" strokeWidth="4" />
      <rect x="13" y="12" width="38" height="27" rx="7" fill="#191a21" stroke="#44475a" strokeWidth="2" />
      <path d="M19 21h8M19 26h14M19 31h6" stroke="#50fa7b" strokeWidth="3" strokeLinecap="round" />
      <circle cx="21" cy="49" r="4.5" fill="#ff79c6" />
      <circle cx="32" cy="49" r="4.5" fill="#50fa7b" />
      <circle cx="43" cy="49" r="4.5" fill="#8be9fd" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="font-mono text-lg font-bold tracking-tight">
      <span className="text-fg">Fliper</span>
      <span className="text-purple">OS</span>
    </span>
  );
}
