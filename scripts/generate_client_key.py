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
    # Not a password hash: api_key is a 256-bit random token, not a human-chosen
    # low-entropy secret - see gateway/auth.py._hash_key for the full reasoning.
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()  # lgtm[py/weak-sensitive-data-hashing]
    clients[args.client_id] = {"key_hash": key_hash}
    CLIENTS_PATH.write_text(json.dumps(clients, indent=2) + "\n")

    print(f"client '{args.client_id}' registered.")
    # Not a log sink: this is a one-time interactive CLI printing a freshly
    # generated credential to the operator's own terminal so they can capture
    # it - the same pattern `aws iam create-access-key` / `gh auth token` use.
    print(f"API key (shown once — store it securely, it cannot be recovered): {api_key}")  # lgtm[py/clear-text-logging-sensitive-data]


if __name__ == "__main__":
    main()
