#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
source_dir=$(realpath -- "${1:?Usage: bash scripts/apply.sh private/rendered-update}")
runtime=/etc/naiveproxy
[[ -d "$runtime/releases" && -x /opt/naiveproxy/hysteria ]]
for file in Caddyfile public-host hy2-direct.json hy2-residential.json; do
  [[ -s "$source_dir/$file" && ! -L "$source_dir/$file" ]]
done
[[ -d "$source_dir/subscriptions" && ! -L "$source_dir/subscriptions" ]]
exec 9>/run/lock/naiveproxy-apply.lock
flock -n 9 || { echo 'Another apply operation is running.' >&2; exit 1; }
old=$(readlink -f "$runtime/current" || true)
if [[ -e "$runtime/current" ]]; then
  [[ -L "$runtime/current" && "$old" == "$runtime/releases/"* ]] || exit 1
fi
stage=$(mktemp -d "$runtime/releases/bundle.XXXXXXXX")
chown root:naiveproxy "$stage"
chmod 0750 "$stage"
for file in Caddyfile public-host hy2-direct.json hy2-residential.json; do
  install -o root -g naiveproxy -m 0640 "$source_dir/$file" "$stage/$file"
done
install -d -o root -g naiveproxy -m 0750 "$stage/subscriptions"
shopt -s nullglob
for file in "$source_dir/subscriptions/"*; do
  name=$(basename -- "$file")
  [[ -f "$file" && ! -L "$file" && "$name" =~ ^[A-Za-z0-9_-]{43}$ ]] || exit 1
  install -o root -g naiveproxy -m 0640 "$file" "$stage/subscriptions/$name"
done
runuser -u naiveproxy -- /opt/naiveproxy/caddy validate --config "$stage/Caddyfile" --adapter caddyfile
units=(naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service)
active=()
for unit in "${units[@]}"; do
  if systemctl is-active --quiet "$unit"; then active+=("$unit"); fi
done
switched=0
recover() {
  result=$?
  if (( result != 0 && switched == 1 )); then
    systemctl stop "${units[@]}" || true
    if [[ -d "$old" && "$old" == "$runtime/releases/"* ]]; then
      ln -s "$old" "$stage.restore"
      mv -Tf "$stage.restore" "$runtime/current"
      if (( ${#active[@]} )); then systemctl start "${active[@]}" || true; fi
      echo 'Apply failed; restored previous bundle. Inspect service logs.' >&2
    else
      echo 'First apply failed; services stopped and files retained for diagnosis.' >&2
    fi
  fi
  exit "$result"
}
trap recover EXIT
# Restart, rather than reload, revokes old HTTP/2 and QUIC sessions as well.
switched=1
systemctl stop "${units[@]}"
ln -s "$stage" "$stage.link"
mv -Tf "$stage.link" "$runtime/current"
systemctl start "${units[@]}"
sleep 3
for unit in "${units[@]}"; do
  systemctl is-active --quiet "$unit"
  [[ $(systemctl show "$unit" -p NRestarts --value) == 0 ]]
done
host=$(cat "$stage/public-host")
curl --fail --silent --show-error --noproxy '*' --resolve "$host:443:127.0.0.1" "https://$host/" -o /dev/null
if [[ -d "$old" && "$old" == "$runtime/releases/"* ]]; then
  ln -s "$old" "$stage.previous"
  mv -Tf "$stage.previous" "$runtime/previous"
fi
echo 'Applied config and subscriptions together; verify all four nodes externally.'
