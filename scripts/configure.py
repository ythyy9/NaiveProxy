#!/usr/bin/env python3
"""Generate private Naive settings and exports; never contact or alter a VPS."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import quote, urlsplit


def host_value(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        raise ValueError("Invalid host")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        labels = value.split(".")
        if len(labels) < 2 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", x) for x in labels):
            raise ValueError("Use a domain name or IPv4 address, without scheme or port")
        return value.lower()
    if address.version != 4:
        raise ValueError("This guide's installer supports IPv4 or a domain name")
    return str(address)


def token(value, password=False):
    pattern = r"[A-Za-z0-9._~-]{20,128}" if password else r"[A-Za-z0-9_-]{1,48}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value) or value.startswith("REPLACE_"):
        raise ValueError("Use a simple account name and a generated URL-safe password (20+ characters)")
    return value


def validate(settings):
    host_value(settings["host"])
    accounts = settings["accounts"]
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list; an empty list serves only the website")
    seen = set()
    upstream = settings.get("residential_upstream")
    if upstream is not None:
        # SOCKS5 is plaintext: only a separately secured, local bridge is accepted.
        p = urlsplit(upstream)
        if (p.scheme != "socks5" or p.hostname != "127.0.0.1" or not p.port
                or not p.username or not p.password or p.path or p.query or p.fragment
                or any(c in upstream for c in "\r\n\t{}\"\\")):
            raise ValueError("residential_upstream must be an authenticated socks5:// URL at 127.0.0.1")
    for account in accounts:
        name = token(account["username"])
        token(account["password"], password=True)
        if name in seen:
            raise ValueError("Duplicate username")
        seen.add(name)
        if account["route"] not in ("direct", "residential"):
            raise ValueError("Unknown route")
        if type(account["enabled"]) is not bool:
            raise ValueError("enabled must be true or false")
        if account["route"] == "residential" and account["enabled"] and not upstream:
            raise ValueError("An enabled residential account needs a local SOCKS bridge")
    return settings


def render_config(settings, *, port=443, admin="127.0.0.1:20190",
                  cert="/etc/naiveproxy/tls/fullchain.pem",
                  key="/etc/naiveproxy/tls/privkey.pem", site="/opt/naiveproxy/site"):
    validate(settings)
    q = json.dumps
    lines = ["{", f"    admin {admin}", "    auto_https off",
             "    servers {", "        protocols h1 h2", "    }",
             "    log {", "        exclude http.log.error", "    }", "}", "",
             f":{port} {{", f"    tls {q(str(cert))} {q(str(key))}", "    route {"]
    for route in ("residential", "direct"):
        accounts = [a for a in settings["accounts"] if a["enabled"] and a["route"] == route]
        if not accounts:
            continue  # An empty forward_proxy block would be an unauthenticated proxy.
        lines.append("        forward_proxy {")
        for a in accounts:
            lines.append(f'            basic_auth {q(a["username"])} {q(a["password"])}')
        lines.extend(["            hide_ip", "            hide_via", "            probe_resistance"])
        if route == "residential":
            lines.append("            upstream " + q(settings["residential_upstream"]))
        lines.append("        }")
    lines.extend([f"        root * {q(str(site))}", "        file_server", "    }", "}", ""])
    return "\n".join(lines)


def write_private(path, text):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    path.chmod(0o600)


def initialize(host, users, output):
    names = [token(name) for name in users]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate user name")
    data = {"host": host_value(host), "residential_upstream": None, "accounts": [
        {"username": name + "-d", "password": secrets.token_urlsafe(32),
         "route": "direct", "enabled": True} for name in names]}
    validate(data)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_private(output, json.dumps(data, indent=2) + "\n")


def export(settings, output):
    validate(settings)
    # Refuse to leave stale exports behind when an account is disabled or deleted.
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    write_private(output / "Caddyfile", render_config(settings))
    write_private(output / "public-host", host_value(settings["host"]) + "\n")
    clients = output / "clients"
    clients.mkdir(mode=0o700)
    for account in settings["accounts"]:
        if not account["enabled"]:
            continue
        name = account["username"]
        authority = f'{quote(name, safe="")}:{quote(account["password"], safe="")}@{host_value(settings["host"])}:443'
        write_private(clients / f"{name}.txt", f"naive+https://{authority}#{quote(name)}\n")
        for protocol, port in (("socks", 1080), ("http", 1081)):
            config = {"listen": f"{protocol}://127.0.0.1:{port}", "proxy": "https://" + authority}
            write_private(clients / f"{name}-{protocol}.json", json.dumps(config, indent=2) + "\n")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--host", required=True)
    init.add_argument("--users", nargs="+", default=["friend1"])
    init.add_argument("--output", type=Path, default=Path("private/settings.json"))
    render = sub.add_parser("render")
    render.add_argument("settings", type=Path)
    render.add_argument("--output", type=Path, default=Path("private/rendered"))
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize(args.host, args.users, args.output)
        else:
            export(json.loads(args.settings.read_text(encoding="utf-8")), args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Configuration failed ({type(error).__name__}); check the input and use a new output path.\n")
    print(f"Created {args.output}; contains credentials, keep private.")


if __name__ == "__main__":
    main()
