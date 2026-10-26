import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class FrontendShellTests(unittest.TestCase):
    def read(self, relative):
        return (FRONTEND / relative).read_text(encoding="utf-8")

    def test_pages_use_relative_assets(self):
        for relative in ("index.html", "auth/callback.html"):
            source = self.read(relative)
            self.assertNotIn('src="/', source)
            self.assertNotIn('href="/', source)

    def test_single_public_base_path(self):
        config = self.read("assets/config.js")
        self.assertIn('basePath: "/attendance-spaces/"', config)
        self.assertIn('callbackPath: "/attendance-spaces/auth/callback.html"', config)
        for relative in ("assets/app.js", "assets/context.js", "assets/auth-callback.js"):
            self.assertNotIn('"/attendance-spaces/', self.read(relative))

    def test_context_values_are_validated_not_authorized(self):
        source = self.read("assets/context.js")
        self.assertIn("spc_", source)
        self.assertIn("cp_", source)
        self.assertIn("inv_", source)
        self.assertNotIn("authorized", source.lower())

    def test_swedish_accessible_shell(self):
        source = self.read("index.html")
        self.assertIn('<html lang="sv">', source)
        self.assertIn('href="#main"', source)
        self.assertIn('aria-live="polite"', source)
        self.assertIn("Logga in", source)


if __name__ == "__main__":
    unittest.main()
