#!/usr/bin/env bash
# Destructive only to the disposable GitHub-hosted test VM. Never run on a VPS.
set -Eeuo pipefail
[[ ${GITHUB_ACTIONS:-} == true && $EUID -eq 0 ]] || exit 1
cleanup() {
  systemctl disable --now naive-cert-renew.timer naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service || true
}
trap cleanup EXIT
apt-get update -qq
apt-get install -y -qq nftables
work=$(realpath .ci)/installation
mkdir -p "$work" /opt/naive-certbot/bin /etc/letsencrypt/live/naiveproxy
# Only ACME issuance is stubbed. Certificate trust, copy/reload, systemd services,
# subscription replacement and Hysteria's real nftables rules run normally.
printf '#!/bin/sh\nexit 0\n' > /opt/naive-certbot/bin/certbot
chmod 0755 /opt/naive-certbot/bin/certbot
lineage=/etc/letsencrypt/live/naiveproxy
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj /CN=localhost \
  -addext subjectAltName=IP:127.0.0.1 -keyout "$lineage/privkey.pem" -out "$lineage/cert.pem" 2>/dev/null
cp "$lineage/cert.pem" "$lineage/chain.pem"
cp "$lineage/cert.pem" "$lineage/fullchain.pem"
cp "$lineage/cert.pem" /usr/local/share/ca-certificates/naive-ci.crt
update-ca-certificates >/dev/null
python3 scripts/configure.py init --host 127.0.0.1 --users alice bob --output "$work/settings.json"
python3 - "$work/settings.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);data=json.loads(p.read_text())
data['residential_upstream']='socks5://bridge:only-ci-test-password@127.0.0.1:28400'
p.write_text(json.dumps(data))
PY
python3 scripts/configure.py render "$work/settings.json" --output "$work/first"
nft --stateless list ruleset > "$work/nft-before"
bash scripts/install.sh "$work/first"
curl --noproxy '*' --fail --silent "$(cat "$work/first/clients/alice/subscription-url.txt")" | base64 -d > "$work/nodes"
[[ $(wc -l < "$work/nodes") == 4 ]]
nft list ruleset > "$work/nft-running"
grep -qi 'hysteria' "$work/nft-running"
python3 - "$work/settings.json" <<'PY'
import json,secrets,sys
from pathlib import Path
p=Path(sys.argv[1]);data=json.loads(p.read_text())
data['clients'][0]['subscription_token']=secrets.token_urlsafe(32)
data['clients'][1]['enabled']=False
p.write_text(json.dumps(data))
PY
python3 scripts/configure.py render "$work/settings.json" --output "$work/second"
bash scripts/apply.sh "$work/second"
for client in alice bob; do
  status=$(curl --noproxy '*' --silent -o /dev/null -w '%{http_code}' "$(cat "$work/first/clients/$client/subscription-url.txt")")
  [[ "$status" == 404 ]]
done
curl --noproxy '*' --fail --silent "$(cat "$work/second/clients/alice/subscription-url.txt")" | base64 -d > "$work/new-nodes"
[[ $(wc -l < "$work/new-nodes") == 4 ]]
bash scripts/renew-hook.sh
systemctl is-active --quiet naive-cert-renew.timer
cleanup
nft --stateless list ruleset > "$work/nft-after"
diff -u "$work/nft-before" "$work/nft-after"
echo 'PASS: real install/apply, service permissions, subscriptions and revocation, certificate hook, nftables lifecycle'
