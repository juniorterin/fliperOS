#!/usr/bin/env bash
# Escreve o cliente OAuth do Google do FliperOS (o "Entrar com o Google" do
# backup na nuvem) em ARQUIVO, a partir de CLIENT_ID e CLIENT_SECRET no
# ambiente: os secrets GOOGLE_OAUTH_CLIENT_ID e GOOGLE_OAUTH_CLIENT_SECRET do
# GitHub Actions. O par fica fora do git (o push protection do GitHub o
# recusa); o build da ISO e o workflow Google OAuth o escrevem.
#
#   CLIENT_ID=... CLIENT_SECRET=... tools/google-oauth-conf.sh ARQUIVO
#
# Sem os dois (um fork sem os secrets), ARQUIVO fica como esta e sai 0: o
# Google Drive so nao aparece no backup na nuvem. Um par mal formado sai 1.
set -euo pipefail
out=${1:?Uso: tools/google-oauth-conf.sh ARQUIVO}
id=${CLIENT_ID:-}
secret=${CLIENT_SECRET:-}
if [[ -z $id && -z $secret ]]; then
  echo "google-oauth-conf: no GOOGLE_OAUTH_CLIENT_ID/SECRET secrets; $out stays as it is"
  exit 0
fi
if [[ ! $id =~ ^[A-Za-z0-9-]+\.apps\.googleusercontent\.com$ || ! $secret =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "google-oauth-conf: the client id or secret is not in the Google format" >&2
  exit 1
fi
# O cabecalho do arquivo do git (os comentarios) fica; so as duas linhas mudam.
head=$(grep '^#' "$out" 2> /dev/null || true)
{
  [[ -n $head ]] && printf '%s\n' "$head"
  printf 'client_id=%s\nclient_secret=%s\n' "$id" "$secret"
} > "$out.tmp"
chmod 644 "$out.tmp"
mv "$out.tmp" "$out"
echo "google-oauth-conf: $out written"
