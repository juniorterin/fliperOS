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
printf 'FliperOS: video diagnostics (no mode will be changed)\n'
uname -sr
printf '\nBoot parameters:\n'
cat /proc/cmdline
printf '\nGPU and driver per device:\n'
command -v lspci >/dev/null && lspci -nnk | grep -A3 -Ei 'VGA|3D controller|Display controller'
printf '\nConnectors (advertised modes do not prove the active mode):\n'
for status in /sys/class/drm/card*-*/status; do
    [[ -f "$status" ]] || continue
    printf '%s: ' "${status%/status}"
    cat "$status"
done
printf '\nInstalled components:\n'
for executable in switchres grid geometry groovymame retroarch pcsx2 flycast supermodel Skyscraper; do
    command -v "$executable" || printf '%s: missing\n' "$executable"
done
printf '\nfliperos-setup configuration (/etc/fliperos/fliperos.conf):\n'
cat /etc/fliperos/fliperos.conf 2>/dev/null || printf '(no output test yet)\n'
printf '\nActive mode:\n'
python3 "$checker" "$@"
exit $?
