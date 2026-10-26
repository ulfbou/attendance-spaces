from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    'README.md', 'LICENSE', 'CONTRIBUTING.md', 'SECURITY.md',
    'frontend/index.html', 'frontend/auth/callback.html',
    'docs/product-and-scope.md', 'docs/architecture.md',
    'docs/security-and-threat-model.md', 'docs/privacy-and-data-handling.md',
    'docs/operations-and-cost.md', 'docs/acceptance.md',
    'docs/portfolio-integration.md', '.github/workflows/validate.yml',
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
if '/attendance-spaces/' not in (ROOT / 'frontend/assets/app.js').read_text(encoding='utf-8'):
    errors.append('configured public base path is missing')
if errors:
    for error in errors:
        print(f'BLOCKED {error}', file=sys.stderr)
    raise SystemExit(1)
print('PASS repository bootstrap contract')
