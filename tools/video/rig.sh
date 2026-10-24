#!/bin/bash
# Monta em /rig/home a pasta pessoal da amostra (o demo.tar do gabinete):
# as listas, a midia, os videos, as informacoes, os favoritos e uma ROM
# vazia para cada arquivo de jogo. O fliperos-setup de mentira responde
# --systems e --filters com o que o gabinete tinha.
set -e
H=/rig/home
rm -rf /rig && mkdir -p $H
# Os arquivos que o frontend grava (favoritos) vao para o usuario do gabinete.
useradd -M -d $H fliperos 2> /dev/null || true
tar xf /v/demo.tar -C $H
sed -i "s#/home/fliperos#$H#g" $H/.cache/fliperos/frontend-systems
while IFS=$'\t' read -r key file; do
  [ -n "$key" ] || continue
  folder=$(awk -F'|' -v k="$key" '$1 == k { print $2; exit }' $H/.cache/fliperos/frontend-systems)
  mkdir -p "$folder"
  : > "$folder/$file"
done < $H/demo-roms.txt
# Os sistemas da amostra; os outros ficam de fora (pastas vazias).
keep=$(cut -f1 $H/demo-roms.txt | sort -u | tr '\n' '|')
awk -F'|' -v keep="|$keep" 'index(keep, "|" $1 "|")' $H/.cache/fliperos/frontend-systems > /rig/systems
cp /rig/systems $H/.cache/fliperos/frontend-systems
cat > /rig/fliperos-setup << EOF
#!/bin/bash
case \$1 in
  --systems) cat /rig/systems ;;
  --filters) cat $H/.cache/fliperos/frontend-filters ;;
  --romlists) sleep 1 ;;
esac
EOF
chmod +x /rig/fliperos-setup
export HOME=$H FLIPEROS_HOME=$H FLIPEROS_SETUP=/rig/fliperos-setup FLIPEROS_BUTTONS_MAP=/nonexistent
export FLIPEROS_VIDEO_AUDIO=null FLIPEROS_WEB_MODULE=/config/fliperos-web PYTHONDONTWRITEBYTECODE=1
cd /g
exec python3 -I "$@"
