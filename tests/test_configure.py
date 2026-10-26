import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("configure", Path(__file__).resolve().parents[1] / "scripts/configure.py")
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def settings(self):
        return {"host": "203.0.113.10", "residential_upstream": None, "accounts": [
            {"username": "friend1-d", "password": "test-password-1234567890", "route": "direct", "enabled": True}]}

    def test_empty_or_disabled_accounts_never_create_open_proxy(self):
        data = self.settings()
        data["accounts"][0]["enabled"] = False
        self.assertNotIn("forward_proxy", configure.render_config(data))
        data["accounts"] = []
        self.assertNotIn("forward_proxy", configure.render_config(data))
        self.assertIn("file_server", configure.render_config(data))

    def test_credentials_are_random_and_existing_settings_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            configure.initialize("proxy.example.com", ["alice", "bob"], path)
            original = path.read_bytes()
            data = json.loads(original)
            self.assertNotEqual(data["accounts"][0]["password"], data["accounts"][1]["password"])
            with self.assertRaises(FileExistsError):
                configure.initialize("proxy.example.com", ["alice"], path)
            self.assertEqual(path.read_bytes(), original)

    def test_disabled_accounts_are_not_exported_and_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "rendered"
            data = self.settings()
            configure.export(data, output)
            client = json.loads((output / "clients/friend1-d-http.json").read_text())
            self.assertEqual(client["listen"], "http://127.0.0.1:1081")
            self.assertTrue(client["proxy"].startswith("https://"))
            with self.assertRaises(FileExistsError):
                configure.export(data, output)
            data["accounts"][0]["enabled"] = False
            configure.export(data, Path(directory) / "disabled")
            self.assertEqual(list((Path(directory) / "disabled/clients").iterdir()), [])

    def test_injection_duplicate_and_route_errors_are_rejected(self):
        for bad in ("bad\n}", "{env.SECRET}", "bad:name"):
            data = self.settings()
            data["accounts"][0]["username"] = bad
            with self.assertRaises(ValueError):
                configure.validate(data)
        data = self.settings()
        data["accounts"].append(data["accounts"][0].copy())
        with self.assertRaises(ValueError):
            configure.validate(data)
        data = self.settings()
        data["accounts"][0]["route"] = "residential"
        with self.assertRaises(ValueError):
            configure.validate(data)

    def test_residential_requires_an_authenticated_local_bridge(self):
        data = self.settings()
        for bad in ("socks5://u:p@203.0.113.20:1080", "http://u:p@127.0.0.1:1080", "socks5://127.0.0.1:1080"):
            data["residential_upstream"] = bad
            with self.assertRaises(ValueError):
                configure.validate(data)
        data["residential_upstream"] = "socks5://bridge:local-test-password@127.0.0.1:28400"
        data["accounts"].append({"username": "friend1-r", "password": "another-test-password-123", "route": "residential", "enabled": True})
        text = configure.render_config(data)
        self.assertLess(text.index('"friend1-r"'), text.index('"friend1-d"'))
        self.assertEqual(text.count("upstream "), 1)


if __name__ == "__main__":
    unittest.main()
