import argparse
import hashlib
import json
import secrets
from pathlib import Path

CLIENTS_PATH = Path(__file__).resolve().parent.parent / "gateway" / "clients.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a new client and generate its API key.")
    parser.add_argument("client_id")
    args = parser.parse_args()

    clients = json.loads(CLIENTS_PATH.read_text()) if CLIENTS_PATH.exists() else {}
    if args.client_id in clients:
        raise SystemExit(f"client '{args.client_id}' already exists")

    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    clients[args.client_id] = {"key_hash": key_hash}
    CLIENTS_PATH.write_text(json.dumps(clients, indent=2) + "\n")

    print(f"client '{args.client_id}' registered.")
    print(f"API key (shown once — store it securely, it cannot be recovered): {api_key}")


if __name__ == "__main__":
    main()
