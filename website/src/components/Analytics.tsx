import Script from 'next/script';
import { GA_ID } from '@/lib/site';

// Google Analytics 4 só no build de produção; NEXT_PUBLIC_GA_ID vazio desliga.
export function Analytics() {
  if (process.env.NODE_ENV !== 'production' || !GA_ID) return null;
  return (
    <>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
      <Script id="ga4" strategy="afterInteractive">
        {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','${GA_ID}');`}
      </Script>
    </>
  );
}
