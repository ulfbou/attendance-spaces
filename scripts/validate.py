from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    'README.md', 'LICENSE', 'CONTRIBUTING.md', 'SECURITY.md',
    'frontend/index.html', 'frontend/auth/callback.html',
    'frontend/assets/auth.js', 'frontend/assets/runtime-config.js',
    'docs/product-and-scope.md', 'docs/architecture.md',
    'docs/security-and-threat-model.md', 'docs/privacy-and-data-handling.md',
    'docs/operations-and-cost.md', 'docs/acceptance.md',
    'docs/portfolio-integration.md', 'docs/authentication-operations.md',
    'infrastructure/cognito.yaml', 'scripts/render_runtime_config.py',
    '.github/workflows/validate.yml',
    '.github/workflows/pages.yml',
]
errors = []
for relative in required:
    path = ROOT / relative
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f'missing or empty: {relative}')
index = (ROOT / 'frontend/index.html').read_text(encoding='utf-8')
for forbidden in ('href="/assets/', 'src="/assets/'):
    if forbidden in index:
        errors.append(f'root-relative asset detected: {forbidden}')
frontend_config = ROOT / 'frontend/assets/config.js'
if not frontend_config.is_file():
    errors.append('frontend public configuration is missing')
else:
    config_source = frontend_config.read_text(encoding='utf-8')
    if 'basePath: "/attendance-spaces/"' not in config_source:
        errors.append('configured public base path is missing')
    if 'callbackPath: "/attendance-spaces/auth/callback.html"' not in config_source:
        errors.append('configured authentication callback path is missing')
auth_source = (ROOT / 'frontend/assets/auth.js').read_text(encoding='utf-8')
for required_auth_marker in ('code_challenge_method: "S256"', 'response_type: "code"', 'code_verifier: transaction.verifier'):
    if required_auth_marker not in auth_source:
        errors.append(f'missing authentication boundary: {required_auth_marker}')
runtime_source = (ROOT / 'frontend/assets/runtime-config.js').read_text(encoding='utf-8')
if 'clientSecret' in runtime_source or 'client_secret' in runtime_source:
    errors.append('public runtime configuration contains a client secret')
if errors:
    for error in errors:
        print(f'BLOCKED {error}', file=sys.stderr)
    raise SystemExit(1)
import json
for schema_path in sorted((ROOT / 'contracts').glob('*.schema.json')):
    try:
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f'invalid contract JSON: {schema_path.relative_to(ROOT)}: {exc}')
        continue
    for key in ('$schema', '$id', 'title'):
        if not schema.get(key):
            errors.append(f'missing {key}: {schema_path.relative_to(ROOT)}')
if errors:
    for error in errors:
        print(f'BLOCKED {error}', file=sys.stderr)
    raise SystemExit(1)
print('PASS repository and contract validation')
