#!/usr/bin/env bash
# Read-only report. Exit status follows the active mode check: 0/1/2.
set -uo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
checker=/usr/local/bin/fliperos-video-check
[[ -x "$checker" ]] || checker="$src/fliperos-video-check.py"
if [[ "${1:-}" == --json ]]; then
    shift
    exec python3 "$checker" --json "$@"
fi
printf 'FliperOS: diagnostico de video (nenhum modo sera alterado)\n'
uname -sr
printf '\nParametros de boot:\n'
cat /proc/cmdline
printf '\nGPU e driver por dispositivo:\n'
command -v lspci >/dev/null && lspci -nnk | grep -A3 -Ei 'VGA|3D controller|Display controller'
printf '\nConectores (modos anunciados nao comprovam modo ativo):\n'
for status in /sys/class/drm/card*-*/status; do
    [[ -f "$status" ]] || continue
    printf '%s: ' "${status%/status}"
    cat "$status"
done
printf '\nComponentes instalados:\n'
for executable in switchres groovymame retroarch pcsx2 flycast supermodel; do
    command -v "$executable" || printf '%s: ausente\n' "$executable"
done
printf '\nServico de verificacao no boot:\n'
systemctl --no-pager status fliperos-video-check.service 2>/dev/null || true
printf '\nModo ativo:\n'
python3 "$checker" "$@"
exit $?
