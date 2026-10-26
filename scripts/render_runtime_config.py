import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets" / "runtime-config.js"


def nonempty(value: str) -> str:
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("value must not be empty")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Render public Cognito browser configuration.")
    parser.add_argument("--region", required=True, type=nonempty)
    parser.add_argument("--user-pool-id", required=True, type=nonempty)
    parser.add_argument("--client-id", required=True, type=nonempty)
    parser.add_argument("--domain", required=True, type=nonempty)
    args = parser.parse_args()
    values = {
        "cognitoRegion": args.region,
        "cognitoUserPoolId": args.user_pool_id,
        "cognitoClientId": args.client_id,
        "cognitoDomain": args.domain.rstrip("/"),
    }
    lines = ["export const runtimeConfig = Object.freeze({"]
    lines.extend(f"  {key}: {json.dumps(value)}," for key, value in values.items())
    lines.append("});")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS rendered {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
