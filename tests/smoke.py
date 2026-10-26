"""Run the real server locally with a trusted test cert, HTTP/2 and Naive padding.

Requires Linux, the downloaded Caddy binary, openssl, and Python h2.
Loopback destinations are allowed ONLY in the temporary test configuration.
"""
import base64
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import DataReceived, ResponseReceived, StreamEnded, StreamReset

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("configure", ROOT / "scripts/configure.py")
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)
PASSWORD = "integration-test-password-123"
MARKER = b"naive-local-origin-ok"


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Origin(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(MARKER)))
        self.end_headers()
        self.wfile.write(MARKER)

    def log_message(self, *args):
        pass


def exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise EOFError("Unexpected SOCKS EOF")
        data += chunk
    return data


class Bridge(socketserver.BaseRequestHandler):
    def handle(self):
        # Test-only SOCKS bridge. It is bound to loopback and dies with the test.
        sock = self.request
        sock.settimeout(5)
        version, count = exact(sock, 2)
        assert version == 5 and 2 in exact(sock, count)
        sock.sendall(b"\x05\x02")
        version, size = exact(sock, 2)
        username = exact(sock, size)
        password = exact(sock, exact(sock, 1)[0])
        assert version == 1 and username == b"bridge" and password == b"test-bridge-password"
        sock.sendall(b"\x01\x00")
        version, command, _, kind = exact(sock, 4)
        assert version == 5 and command == 1
        if kind == 1:
            host = socket.inet_ntoa(exact(sock, 4))
        elif kind == 3:
            host = exact(sock, exact(sock, 1)[0]).decode()
        else:
            raise AssertionError("Unexpected address type")
        target_port = int.from_bytes(exact(sock, 2), "big")
        assert host == "127.0.0.1" and target_port == self.server.origin_port
        self.server.hits += 1
        with socket.create_connection((host, target_port), timeout=5) as target:
            sock.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")
            request = b""
            while b"\r\n\r\n" not in request:
                request += exact(sock, 1)
            target.sendall(request)
            while True:
                chunk = target.recv(65536)
                if not chunk:
                    break
                sock.sendall(chunk)


def h2_tunnel(context, server_port, origin_port, username):
    context.set_alpn_protocols(["h2"])
    with socket.create_connection(("127.0.0.1", server_port), timeout=5) as tcp:
        with context.wrap_socket(tcp, server_hostname="127.0.0.1") as tls:
            assert tls.selected_alpn_protocol() == "h2"
            conn = H2Connection(config=H2Configuration(client_side=True, header_encoding="utf-8", validate_outbound_headers=False))
            conn.initiate_connection()
            auth = base64.b64encode(f"{username}:{PASSWORD}".encode()).decode()
            conn.send_headers(1, [(":method", "CONNECT"), (":authority", f"127.0.0.1:{origin_port}"),
                                  ("proxy-authorization", "Basic " + auth), ("padding", "test-padding-header-1234567890")])
            tls.sendall(conn.data_to_send())
            padded = bytearray()
            received_headers = False
            ended = False
            while not ended:
                data = tls.recv(65536)
                assert data, "Unexpected HTTP/2 EOF"
                for event in conn.receive_data(data):
                    if isinstance(event, ResponseReceived):
                        headers = dict(event.headers)
                        assert headers[":status"] == "200", headers
                        assert "padding" in headers, "Naive response padding header missing"
                        received_headers = True
                        request = b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
                        frame = len(request).to_bytes(2, "big") + b"\x07" + request + bytes(7)
                        # This single-request test has no more upload data.
                        conn.send_data(1, frame, end_stream=True)
                    elif isinstance(event, DataReceived):
                        padded.extend(event.data)
                        conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                    elif isinstance(event, StreamEnded):
                        ended = True
                    elif isinstance(event, StreamReset):
                        raise AssertionError(f"HTTP/2 stream reset: {event.error_code}, received {len(padded)} bytes")
                pending = conn.data_to_send()
                if pending:
                    tls.sendall(pending)
            assert received_headers
            decoded = bytearray()
            for _ in range(8):
                if not padded:
                    break
                assert len(padded) >= 3
                size = int.from_bytes(padded[:2], "big")
                padding = padded[2]
                assert len(padded) >= 3 + size + padding
                decoded.extend(padded[3:3 + size])
                del padded[:3 + size + padding]
            decoded.extend(padded)
            assert b"200 OK" in decoded and MARKER in decoded, "Payload padding round trip failed"


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
        settings = {"host": "127.0.0.1", "residential_upstream": f"socks5://bridge:test-bridge-password@127.0.0.1:{bridge.server_address[1]}",
                    "accounts": [{"username": name, "password": PASSWORD, "enabled": True, "route": route}
                                 for name, route in (("alice-d", "direct"), ("alice-r", "residential"))]}
        server_port = port()
        config = configure.render_config(settings, port=server_port, admin="off", cert=cert, key=key, site=ROOT / "site")
        config = config.replace("            hide_ip", "            acl {\n                allow 127.0.0.1/32\n            }\n            hide_ip")
        path = work / "Caddyfile"
        path.write_text(config)
        subprocess.run([binary, "validate", "--config", str(path), "--adapter", "caddyfile"], check=True)
        with (work / "server.log").open("w") as log:
            process = subprocess.Popen([binary, "run", "--config", str(path), "--adapter", "caddyfile"], stdout=log, stderr=log)
            try:
                context = ssl.create_default_context(cafile=str(cert))
                for attempt in range(50):
                    if process.poll() is not None:
                        raise AssertionError("Caddy exited: " + (work / "server.log").read_text())
                    try:
                        with socket.create_connection(("127.0.0.1", server_port), timeout=.1):
                            break
                    except OSError:
                        time.sleep(.1)
                for method, target, headers in (("GET", "/", {}), ("GET", "/about.html", {}),
                        ("CONNECT", f"127.0.0.1:{origin.server_port}", {}),
                        ("CONNECT", f"127.0.0.1:{origin.server_port}", {"Proxy-Authorization": "Basic " + base64.b64encode(b"alice-d:wrong").decode()})):
                    connection = http.client.HTTPSConnection("127.0.0.1", server_port, context=context, timeout=5)
                    connection.request(method, target, headers=headers)
                    response = connection.getresponse()
                    assert response.getheader("Proxy-Authenticate") is None
                    if method == "GET":
                        assert response.status == 200 and "札记" in response.read().decode()
                    else:
                        assert not 200 <= response.status < 300 and response.status != 407
                    connection.close()
                h2_tunnel(context, server_port, origin.server_port, "alice-d")
                assert bridge.hits == 0, "Direct traffic entered the residential bridge"
                h2_tunnel(context, server_port, origin.server_port, "alice-r")
                assert bridge.hits == 1, "Residential traffic bypassed its bridge"
                print("PASS: website, TLS verification, unauthenticated/wrong-auth denial, HTTP/2, bidirectional padding, direct/residential routing")
            finally:
                process.terminate()
                process.wait(timeout=10)
                for server in (origin, bridge):
                    server.shutdown()
                    server.server_close()


if __name__ == "__main__":
    main()
