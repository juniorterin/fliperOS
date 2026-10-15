# shellcheck shell=bash
# Setup > System > Password: a senha do usuario do gabinete (fliperos), a
# mesma no login, no sudo, no SSH e no compartilhamento da rede. O Samba tem
# a senha dele (o smbpasswd do fliperos-mkiso.sh): as duas mudam juntas.

PASSWORD_MIN=4

# password_valid SENHA: pelo menos PASSWORD_MIN caracteres, numa linha.
password_valid() {
  ((${#1} >= PASSWORD_MIN)) && [[ $1 != *$'\n'* ]]
}

# password_set SENHA troca a senha do FLIPEROS_USER. A senha so passa pela
# entrada dos programas (printf e um builtin: nao aparece no ps) e nunca vai
# para o log. Status 1: senha invalida ou o chpasswd falhou; 2: a do sistema
# mudou e a do Samba nao.
password_set() {
  local pass=$1 user=$FLIPEROS_USER
  password_valid "$pass" || return 1
  printf '%s:%s\n' "$user" "$pass" | chpasswd 2>> "$FLIPEROS_LOG" || return 1
  log_info "senha de $user trocada"
  have smbpasswd || return 0
  if ! printf '%s\n%s\n' "$pass" "$pass" | smbpasswd -s -a "$user" >> "$FLIPEROS_LOG" 2>&1; then
    log_info "smbpasswd falhou: a senha do Samba ficou a de antes"
    return 2
  fi
  return 0
}
