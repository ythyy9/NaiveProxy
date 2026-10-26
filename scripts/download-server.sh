#!/usr/bin/env bash
set -Eeuo pipefail
# Version used by the source deployment. Update the version AND digest together.
version=v2.11.7-naive2
digest=c273dc07dd79c5919f97639cbdcb559d40ce90475dbd8aac80641b0a8c8065ff
destination=${1:?Usage: bash scripts/download-server.sh /path/to/caddy}
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Requires Linux x86_64.' >&2; exit 1; }
[[ ! -e "$destination" ]] || { echo 'Destination already exists.' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
  "https://github.com/klzgrad/forwardproxy/releases/download/$version/caddy-forwardproxy-naive.tar.xz" \
  -o "$work/server.tar.xz"
printf '%s  %s\n' "$digest" "$work/server.tar.xz" | sha256sum --check --status
tar -xJf "$work/server.tar.xz" -C "$work" \
  caddy-forwardproxy-naive/caddy caddy-forwardproxy-naive/LICENSE
"$work/caddy-forwardproxy-naive/caddy" list-modules | grep -Fx 'http.handlers.forward_proxy'
install -m 0755 "$work/caddy-forwardproxy-naive/caddy" "$destination"
install -m 0644 "$work/caddy-forwardproxy-naive/LICENSE" "${destination}.LICENSE"
