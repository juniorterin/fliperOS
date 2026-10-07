import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '404 | FliperOS',
  robots: { index: false, follow: true },
};

// Fora de /en e /pt não há idioma na URL: a página fala os dois.
export default function GlobalNotFound() {
  return (
    <html lang="en-US">
      <body className="flex min-h-dvh items-center justify-center px-6">
        <main className="max-w-md text-center">
          <p className="font-mono text-sm text-green">404</p>
          <h1 className="mt-4 text-3xl font-bold text-fg">Page not found</h1>
          <p lang="pt-BR" className="mt-2 text-muted">
            Página não encontrada
          </p>
          <nav className="mt-8 flex justify-center gap-4 font-mono text-sm">
            <a href="/en" hrefLang="en-US" className="rounded-lg border border-line px-4 py-2 text-fg hover:border-purple">
              FliperOS (English)
            </a>
            <a href="/pt" hrefLang="pt-BR" className="rounded-lg border border-line px-4 py-2 text-fg hover:border-purple">
              FliperOS (Português)
            </a>
          </nav>
        </main>
      </body>
    </html>
  );
}
