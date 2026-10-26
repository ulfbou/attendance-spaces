import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


class AuthenticationBoundaryTests(unittest.TestCase):
    def read(self, name):
        return (ASSETS / name).read_text(encoding="utf-8")

    def test_public_runtime_configuration_has_no_secret(self):
        source = self.read("runtime-config.js")
        self.assertNotIn("clientSecret", source)
        self.assertNotIn("client_secret", source)
        self.assertIn('cognitoClientId: ""', source)

    def test_login_uses_fresh_pkce_s256_and_state(self):
        source = self.read("auth.js")
        self.assertIn('crypto.getRandomValues', source)
        self.assertIn('crypto.subtle.digest("SHA-256"', source)
        self.assertIn('code_challenge_method: "S256"', source)
        self.assertIn('response_type: "code"', source)
        self.assertIn('state,', source)
        self.assertIn('identity_provider: "Google"', source)

    def test_callback_is_bounded_single_use_and_fails_closed(self):
        source = self.read("auth.js")
        self.assertIn("TRANSACTION_MAX_AGE_MS", source)
        self.assertIn("sessionStorage.removeItem(TRANSACTION_KEY)", source)
        self.assertIn("if (!equalText(state, transaction.state))", source)
        self.assertIn("clearSession();", source)
        self.assertIn("code_verifier: transaction.verifier", source)

    def test_browser_claims_do_not_grant_space_roles(self):
        source = self.read("auth.js")
        self.assertNotIn('role:', source)
        self.assertNotIn('OWNER', source)
        self.assertNotIn('PARTICIPANT', source)
        threat_model = (ROOT / "docs/security-and-threat-model.md").read_text(encoding="utf-8")
        self.assertIn("Lambda must independently verify", threat_model)
        self.assertIn("space-local membership", threat_model)

    def test_callback_removes_sensitive_query_and_restores_validated_context(self):
        source = self.read("auth-callback.js")
        self.assertIn("history.replaceState", source)
        self.assertIn("restoreContextUrl(result.context)", source)
        self.assertNotIn("console.", source)


if __name__ == "__main__":
    unittest.main()

class CognitoInfrastructureTests(unittest.TestCase):
    def test_cognito_stack_is_lite_public_pkce_client_with_google(self):
        source = (ROOT / "infrastructure/cognito.yaml").read_text(encoding="utf-8")
        self.assertIn("UserPoolTier: LITE", source)
        self.assertIn("GenerateSecret: false", source)
        self.assertIn("ProviderType: Google", source)
        self.assertIn("AllowedOAuthFlows:\n        - code", source)
        self.assertIn("NoEcho: true", source)
        self.assertNotIn("API Gateway", source)

    def test_pages_uses_only_public_repository_variables(self):
        source = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn("vars.COGNITO_CLIENT_ID", source)
        self.assertNotIn("secrets.GOOGLE", source)
        self.assertIn("render_runtime_config.py", source)
