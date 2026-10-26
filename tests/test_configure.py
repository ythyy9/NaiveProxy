import base64
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit, unquote

spec = importlib.util.spec_from_file_location("configure", Path(__file__).resolve().parents[1] / "scripts/configure.py")
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def settings(self):
        data = configure.new_settings("203.0.113.10", ["alice", "bob"])
        data["residential_upstream"] = "socks5://bridge:test-bridge-password@127.0.0.1:28400"
        return data

    def test_one_subscription_per_client_exactly_four_isolated_nodes(self):
        data = self.settings()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            configure.export(data, output)
            self.assertEqual(len(list((output / "subscriptions").iterdir())), 2)
            for client in data["clients"]:
                nodes = base64.b64decode((output / "subscriptions" / client["subscription_token"]).read_text()).decode().splitlines()
                self.assertEqual(len(nodes), 4)
                self.assertEqual([urlsplit(x).scheme for x in nodes], ["naive+https", "naive+https", "hysteria2", "hysteria2"])
                self.assertEqual(len(set(urlsplit(x).username for x in nodes)), 4)
                other = next(c for c in data["clients"] if c != client)
                for protocol in configure.PROTOCOLS:
                    for route in configure.ROUTES:
                        self.assertNotIn(other[protocol][route]["password"], "\n".join(nodes))
                link = (output / "clients" / client["id"] / "subscription-url.txt").read_text().strip()
                self.assertEqual(link, "https://" + data["host"] + "/s/" + client["subscription_token"])
                for index, route in ((2, "direct"), (3, "residential")):
                    parsed = urlsplit(nodes[index])
                    query = parse_qs(parsed.query)
                    self.assertEqual(query["obfs"], ["salamander"])
                    self.assertEqual(query["insecure"], ["0"])
                    options = data["hy2"][route]
                    self.assertEqual(query["mport"], [f'{options["port_start"]}-{options["port_end"]}'])
                    server = json.loads((output / f"hy2-{route}.json").read_text())
                    self.assertEqual(server["auth"]["userpass"][unquote(parsed.username)], unquote(parsed.password))

    def test_empty_or_disabled_clients_leave_no_old_auth_or_subscription(self):
        data = self.settings()
        original = copy.deepcopy(data)
        for client in data["clients"]:
            client["enabled"] = False
        self.assertNotIn("forward_proxy", configure.render_config(data))
        for route in configure.ROUTES:
            auth = configure.render_hy2(data, route)["auth"]
            self.assertEqual(auth["type"], "password")
            self.assertNotIn(auth["password"], json.dumps(original))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            configure.export(data, output)
            self.assertEqual(list((output / "subscriptions").iterdir()), [])
        data["clients"] = []
        self.assertNotIn("forward_proxy", configure.render_config(data))

    def test_credentials_random_stable_on_render_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            configure.initialize("proxy.example.com", ["alice", "bob"], path)
            original = path.read_bytes()
            data = json.loads(original)
            self.assertNotEqual(data["clients"][0]["subscription_token"], data["clients"][1]["subscription_token"])
            passwords = [c[p][r]["password"] for c in data["clients"] for p in configure.PROTOCOLS for r in configure.ROUTES]
            self.assertEqual(len(passwords), len(set(passwords)))
            with self.assertRaises(FileExistsError):
                configure.initialize("proxy.example.com", ["alice"], path)
            self.assertEqual(path.read_bytes(), original)
            data["residential_upstream"] = self.settings()["residential_upstream"]
            for name in ("one", "two"):
                configure.export(data, Path(directory) / name)
            self.assertEqual((Path(directory) / "one/clients/alice/subscription-url.txt").read_bytes(),
                             (Path(directory) / "two/clients/alice/subscription-url.txt").read_bytes())
            with self.assertRaises(FileExistsError):
                configure.export(data, Path(directory) / "one")

    def test_missing_home_never_creates_fake_four_node_output(self):
        data = configure.new_settings("203.0.113.10", ["alice"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            with self.assertRaises(ValueError):
                configure.export(data, output)
            self.assertFalse(output.exists())

    def test_injection_duplicate_and_overlapping_ranges_rejected(self):
        for bad in ("bad\n}", "{env.SECRET}", "bad:name"):
            data = self.settings()
            data["clients"][0]["naive"]["direct"]["username"] = bad
            with self.assertRaises(ValueError):
                configure.validate(data)
        data = self.settings()
        data["clients"][1]["subscription_token"] = data["clients"][0]["subscription_token"]
        with self.assertRaises(ValueError):
            configure.validate(data)
        data = self.settings()
        data["hy2"]["residential"]["port_start"] = 28010
        with self.assertRaises(ValueError):
            configure.validate(data)

    def test_home_uses_only_local_bridge_without_direct_fallback(self):
        data = self.settings()
        for bad in ("socks5://u:p@203.0.113.20:1080", "http://u:p@127.0.0.1:1080", "socks5://127.0.0.1:1080"):
            data["residential_upstream"] = bad
            with self.assertRaises(ValueError):
                configure.validate(data)
        data = self.settings()
        home = configure.render_hy2(data, "residential")
        self.assertEqual(len(home["outbounds"]), 1)
        self.assertEqual(home["outbounds"][0]["type"], "socks5")
        self.assertTrue(home["disableUDP"])
        self.assertFalse(configure.render_hy2(data, "direct")["disableUDP"])
        self.assertEqual(configure.render_config(data).count("upstream "), 1)


if __name__ == "__main__":
    unittest.main()
