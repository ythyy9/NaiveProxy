#!/usr/bin/env bash
set -Eeuo pipefail
version=app/v2.13.0
digest=907ba8c9693edb104b20582681fb7dc15639d5b64a9cbb616a7b539190a86691
destination=${1:?Usage: bash scripts/download-hy2.sh /path/to/hysteria}
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Requires Linux x86_64.' >&2; exit 1; }
[[ ! -e "$destination" ]] || { echo 'Destination already exists.' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
  "https://github.com/HyNetworks/hysteria/releases/download/$version/hysteria-linux-amd64" -o "$work/hysteria"
printf '%s  %s\n' "$digest" "$work/hysteria" | sha256sum --check --status
install -m 0755 "$work/hysteria" "$destination"
"$destination" version
