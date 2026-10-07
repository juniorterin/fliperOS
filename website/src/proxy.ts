import { NextResponse, type NextRequest } from 'next/server';
import { LOCALE_COOKIE, isLocale, localeFromAcceptLanguage, localePath } from '@/i18n';

// A raiz escolhe o idioma: o cookie do seletor PT|EN e, sem ele, o
// Accept-Language. Robôs sem Accept-Language caem no inglês (x-default).
export function proxy(request: NextRequest) {
  const cookie = request.cookies.get(LOCALE_COOKIE)?.value;
  const locale = isLocale(cookie) ? cookie : localeFromAcceptLanguage(request.headers.get('accept-language'));
  const url = request.nextUrl.clone();
  url.pathname = localePath(locale);
  const response = NextResponse.redirect(url, 307);
  response.headers.set('Vary', 'Accept-Language, Cookie');
  return response;
}

export const config = {
  matcher: '/',
};
