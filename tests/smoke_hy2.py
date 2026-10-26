"""Exercise native HY2 auth, Salamander, port changes and both egress routes.

Unprivileged UDP relays model the multiple entry ports here. The separate install
smoke test checks actual systemd/CAP_NET_ADMIN and Hysteria's nftables setup.
"""
import copy
import json
from pathlib import Path
import selectors
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

from smoke import Bridge, Origin, MARKER, configure, port


class Relays:
    def __init__(self, target):
        self.selector, self.sockets, self.links = selectors.DefaultSelector(), [], {}
        self.visited, self.stopped = set(), threading.Event()
        self.target = target
        self.ports = []
        for _ in range(8):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 0))
            self.ports.append(sock.getsockname()[1])
            self.sockets.append(sock)
            self.selector.register(sock, selectors.EVENT_READ, None)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stopped.is_set():
            for key, _ in self.selector.select(.1):
                payload, sender = key.fileobj.recvfrom(65535)
                if key.data is None:
                    self.visited.add(key.fileobj.getsockname()[1])
                    identity = (key.fd, sender)
                    if identity not in self.links:
                        upstream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        upstream.connect(self.target)
                        self.sockets.append(upstream)
                        self.links[identity] = upstream
                        self.selector.register(upstream, selectors.EVENT_READ, (key.fileobj, sender))
                    self.links[identity].send(payload)
                else:
                    listener, recipient = key.data
                    listener.sendto(payload, recipient)

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=3)
        self.selector.close()
        for sock in self.sockets:
            sock.close()


def request(local_port, origin_port):
    return subprocess.run(["curl", "--fail", "--silent", "--show-error", "--noproxy", "",
                           "--proxy", f"socks5h://127.0.0.1:{local_port}", "--max-time", "5",
                           f"http://127.0.0.1:{origin_port}/"], capture_output=True)


def main():
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        cert, key = work / "cert.pem", work / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1",
                        "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
        origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
        bridge = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Bridge)
        bridge.daemon_threads = True
        bridge.origin_port, bridge.hits = origin.server_port, 0
        for server in (origin, bridge):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        settings = configure.new_settings("127.0.0.1", ["alice", "bob"])
        settings["residential_upstream"] = f"socks5://bridge:test-bridge-password@127.0.0.1:{bridge.server_address[1]}"
        processes, relays, handles, clients = [], [], [], {}
        bridge_closed = False

        def launch(name, mode, config):
            path = work / f"{name}.json"
            path.write_text(json.dumps(config))
            log = (work / f"{name}.log").open("wb")
            handles.append(log)
            process = subprocess.Popen([binary, mode, "--config", str(path), "--log-level", "warn"], stdout=log, stderr=log)
            processes.append(process)
            return process

        try:
            for route in configure.ROUTES:
                server_port = port()
                config = configure.render_hy2(settings, route, cert=cert, key=key)
                config["listen"] = f"127.0.0.1:{server_port}"
                config["acl"] = {"inline": ["exit(all)"]}  # Test-only local origin.
                launch(route + "-server", "server", config)
                relay = Relays(("127.0.0.1", server_port))
                relays.append(relay)
                client = configure.hy2_client(settings, settings["clients"][0], route)
                client["server"] = "127.0.0.1:" + ",".join(map(str, relay.ports))
                client["tls"]["ca"] = str(cert)
                client["transport"]["udp"]["hopInterval"] = "5s"
                local_port = port()
                client["socks5"]["listen"] = f"127.0.0.1:{local_port}"
                process = launch(route + "-client", "client", client)
                clients[route] = (local_port, client)
                for attempt in range(50):
                    if process.poll() is not None:
                        raise AssertionError("HY2 client exited: " + (work / f"{route}-client.log").read_text())
                    result = request(local_port, origin.server_port)
                    if result.returncode == 0:
                        assert result.stdout == MARKER
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("Native HY2 request failed")
                if route == "direct":
                    assert bridge.hits == 0, "Direct route used home bridge"
                else:
                    assert bridge.hits > 0, "Home route bypassed its bridge"
                bad = copy.deepcopy(client)
                bad["auth"] += "-wrong"
                bad["socks5"]["listen"] = f"127.0.0.1:{port()}"
                bad_process = launch(route + "-bad-auth", "client", bad)
                assert bad_process.wait(timeout=12) != 0, "Wrong auth accepted"
                assert "authentication" in (work / f"{route}-bad-auth.log").read_text().lower()
            # Keep requests active across changes; stop as soon as both routes hopped.
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                for local_port, _ in clients.values():
                    result = request(local_port, origin.server_port)
                    assert result.returncode == 0 and result.stdout == MARKER
                if all(len(relay.visited) >= 2 for relay in relays):
                    break
                time.sleep(1)
            assert all(len(relay.visited) >= 2 for relay in relays), "No observed port change"
            bridge.shutdown()
            bridge.server_close()
            bridge_closed = True
            assert request(clients["residential"][0], origin.server_port).returncode != 0, "Unexpected direct fallback"
            assert request(clients["direct"][0], origin.server_port).stdout == MARKER
            print("PASS: native HY2, userpass rejection, Salamander, trusted TLS, both egress routes, port changes, no home fallback")
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
            for relay in relays:
                relay.close()
            for handle in handles:
                handle.close()
            if not bridge_closed:
                bridge.shutdown()
                bridge.server_close()
            origin.shutdown()
            origin.server_close()


if __name__ == "__main__":
    main()
