import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.audit_log import verify_log  # noqa: E402


def main() -> None:
    ok, message = verify_log()
    print(message)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
