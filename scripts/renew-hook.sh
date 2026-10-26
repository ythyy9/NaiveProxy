#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
lineage=/etc/letsencrypt/live/naiveproxy
[[ ${RENEWED_LINEAGE:-$lineage} == "$lineage" ]] || exit 0
[[ -d /etc/naiveproxy/tls ]] || exit 0
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt \
  -untrusted "$lineage/chain.pem" "$lineage/cert.pem"
openssl x509 -in "$lineage/cert.pem" -noout -checkend 0
certkey=$(openssl x509 -in "$lineage/cert.pem" -pubkey -noout | openssl pkey -pubin -outform DER | sha256sum)
privatekey=$(openssl pkey -in "$lineage/privkey.pem" -pubout -outform DER | sha256sum)
[[ "$certkey" == "$privatekey" ]] || { echo 'Certificate/key mismatch.' >&2; exit 1; }
install -o root -g naiveproxy -m 0640 "$lineage/fullchain.pem" /etc/naiveproxy/tls/fullchain.pem
install -o root -g naiveproxy -m 0640 "$lineage/privkey.pem" /etc/naiveproxy/tls/privkey.pem
if [[ -f /etc/naiveproxy/current/Caddyfile ]]; then
  runuser -u naiveproxy -- /opt/naiveproxy/caddy validate --config /etc/naiveproxy/current/Caddyfile --adapter caddyfile
fi
if systemctl is-active --quiet naiveproxy.service; then
  # Certificate paths stay the same; --force is necessary to load their new bytes.
  systemctl reload naiveproxy.service
fi
# Hysteria reads the certificate on each new TLS handshake; no restart is needed.
