import Script from 'next/script';
import { AnalyticsEvents } from '@/components/AnalyticsEvents';
import { CONSENT_KEY } from '@/lib/analytics';
import { GA_ID } from '@/lib/site';

// Google Analytics 4 só no build de produção; NEXT_PUBLIC_GA_ID vazio desliga.
// Consent Mode v2: sem o "aceitar" do aviso de cookies, o GA4 recebe só
// sinais anônimos, sem gravar cookies.
export function Analytics({ locale }: { locale: string }) {
  if (process.env.NODE_ENV !== 'production' || !GA_ID) return null;
  const init = [
    'window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}window.gtag=gtag;',
    `var c=null;try{c=localStorage.getItem('${CONSENT_KEY}')}catch(e){}`,
    "gtag('consent','default',{analytics_storage:c==='granted'?'granted':'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',wait_for_update:500});",
    "gtag('js',new Date());",
    `gtag('config','${GA_ID}',{content_group:'${locale}',language:'${locale}'});`,
  ].join('');
  return (
    <>
      <Script id="ga4" strategy="afterInteractive">
        {init}
      </Script>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
      <AnalyticsEvents />
    </>
  );
}
