#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Requires Linux x86_64.' >&2; exit 1; }
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
rendered=$(realpath -- "${1:?Usage: bash scripts/install.sh private/rendered}")
for command in python3 curl tar xz sha256sum openssl runuser systemctl nft flock; do command -v "$command" >/dev/null; done
[[ -d /run/systemd/system ]] || { echo 'A running systemd system is required.' >&2; exit 1; }
for path in /etc/naiveproxy /opt/naiveproxy /etc/systemd/system/naiveproxy.service \
  /etc/systemd/system/naive-cert-renew.service /etc/systemd/system/naive-cert-renew.timer /etc/systemd/system/naive-hy2@.service \
  /etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy; do
  [[ ! -e "$path" ]] || { echo "Existing path: $path; follow the update guide instead." >&2; exit 1; }
done
if getent passwd naiveproxy >/dev/null || getent group naiveproxy >/dev/null; then
  echo 'Existing naiveproxy service account; inspect it before installing.' >&2; exit 1
fi
[[ -s "$rendered/Caddyfile" && -s "$rendered/public-host" && -d "$rendered/subscriptions" ]]
[[ -x /opt/naive-certbot/bin/certbot ]]
python3 - "$rendered" <<'PY'
import json,socket,sys
from pathlib import Path
for port in (443, 20190):
    with socket.socket() as sock:
        sock.bind(('0.0.0.0', port))
for route in ('direct','residential'):
    config=json.loads((Path(sys.argv[1])/f'hy2-{route}.json').read_text())
    start,end=map(int,config['listen'].rsplit(':',1)[1].split('-'))
    for port in range(start,end+1):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.bind(('0.0.0.0',port))
PY
host=$(cat "$rendered/public-host")
if python3 -c 'import ipaddress,sys; ipaddress.IPv4Address(sys.argv[1])' "$host" 2>/dev/null; then
  openssl x509 -in /etc/letsencrypt/live/naiveproxy/cert.pem -noout -checkip "$host"
else
  openssl x509 -in /etc/letsencrypt/live/naiveproxy/cert.pem -noout -checkhost "$host"
fi
work=$(mktemp -d)
cleanup() {
  result=$?
  rm -rf -- "$work"
  if (( result != 0 )); then
    echo 'Installation stopped. New files, if any, are retained; see docs/operations.md.' >&2
  fi
  exit "$result"
}
trap cleanup EXIT
bash "$root/scripts/download-server.sh" "$work/caddy"
bash "$root/scripts/download-hy2.sh" "$work/hysteria"
useradd --system --user-group --home-dir /var/lib/naiveproxy --no-create-home --shell /usr/sbin/nologin naiveproxy
install -d -o root -g naiveproxy -m 0750 /etc/naiveproxy /etc/naiveproxy/tls /etc/naiveproxy/releases
install -d -o root -g root -m 0755 /opt/naiveproxy /opt/naiveproxy/site
install -m 0755 "$work/caddy" /opt/naiveproxy/caddy
install -m 0755 "$work/hysteria" /opt/naiveproxy/hysteria
install -m 0644 "$work/caddy.LICENSE" /opt/naiveproxy/caddy.LICENSE
install -m 0644 "$root/site/"*.html /opt/naiveproxy/site/
bash "$root/scripts/renew-hook.sh"
install -m 0644 "$root/systemd/"* /etc/systemd/system/
install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
install -m 0750 "$root/scripts/renew-hook.sh" /etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy
systemctl daemon-reload
systemd-analyze verify naiveproxy.service naive-cert-renew.service naive-cert-renew.timer \
  naive-hy2@direct.service naive-hy2@residential.service
bash "$root/scripts/apply.sh" "$rendered"
systemctl enable naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service
systemctl enable --now naive-cert-renew.timer
systemctl is-active --quiet naiveproxy.service
systemctl is-active --quiet naive-cert-renew.timer
echo 'Installed. Run the external checks in docs/installation.md before sharing a node.'
